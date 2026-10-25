import os
import pty
import signal

import select
import re
import time


class TerminalPTY:
    ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
    MAX_IDLE_TIMEOUT = 30.0
    MAX_TIMEOUT = 30.0

    def __init__(self):
        self.closed = False
        shell = "bash"
        self.pid, self.fd = pty.fork()

        if self.pid == 0:
            os.execvp(shell, [shell])

        self._drain_initial_output()

    def _drain_initial_output(self):
        buffer = ""

        while True:
            r, _, _ = select.select([self.fd], [], [], 0.1)
            if self.fd in r:
                data = os.read(self.fd, 1024)
                if not data:
                    break
                buffer += data.decode(errors="ignore")
            else:
                break

        return buffer

    def _normalize_output(self, texto):
        return self.ANSI_RE.sub("", texto)

    def _trim_lines(self, text, head, tail):
        # Si vienen ambos → priorizar tail
        if head is not None and tail is not None:
            head = None  # ignoramos head

        if head is None and tail is None:
            return text

        lineas = text.splitlines()

        if head is not None:
            return "\n".join(lineas[:head])

        if tail is not None:
            return "\n".join(lineas[-tail:])

        return text

    def execute(self, command, pattern=None, idle_timeout=MAX_IDLE_TIMEOUT, max_timeout=MAX_TIMEOUT, head_lines=None, tail_lines=None, ):
        if self.closed:
            raise RuntimeError("Terminal PTY is closed")
        os.write(self.fd, (command + "\n").encode())
        idle_timeout = min(idle_timeout, self.MAX_IDLE_TIMEOUT)
        max_timeout = min(max_timeout, self.MAX_TIMEOUT)

        buffer = ""
        ultimo_dato = time.time()
        inicio = time.time()

        while True:
            if time.time() - inicio > max_timeout:
                buffer = self._normalize_output(buffer)
                buffer = self._trim_lines(buffer, head_lines, tail_lines)
                return buffer

            r, _, _ = select.select([self.fd], [], [], 0.1)

            if self.fd in r:
                data = os.read(self.fd, 1024)
                if not data:
                    buffer = self._normalize_output(buffer)
                    buffer = self._trim_lines(buffer, head_lines, tail_lines)
                    return buffer

                texto = data.decode(errors="ignore")
                buffer += texto
                ultimo_dato = time.time()

                if pattern and re.search(pattern, buffer):
                    buffer = self._normalize_output(buffer)
                    buffer = self._trim_lines(buffer, head_lines, tail_lines)
                    return buffer

            else:
                if time.time() - ultimo_dato > idle_timeout:
                    buffer = self._normalize_output(buffer)
                    buffer = self._trim_lines(buffer, head_lines, tail_lines)
                    return buffer

    def close(self):
        if getattr(self, "closed", False):
            return
        self.closed = True

        try:
            pgid = os.getpgid(self.pid)
            os.killpg(pgid, signal.SIGTERM)
            time.sleep(0.2)

            pid, _ = os.waitpid(self.pid, os.WNOHANG)
            if pid == 0:
                os.killpg(pgid, signal.SIGKILL)
                os.waitpid(self.pid, 0)
        except ProcessLookupError:
            pass
        except OSError:
            pass
        finally:
            try:
                os.close(self.fd)
            except OSError:
                pass

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


if __name__ == "__main__":
    terminal = TerminalPTY()

    salida = terminal.execute("pwd")
    print(salida)

    salida = terminal.execute("python", r">>> ")
    print(salida)

    salida = terminal.execute('print("hola desde python")', r">>> ")
    print(salida)

    salida = terminal.execute("exit()", r"\$ ")
    print(salida)

    terminal.close()
    print()
