from __future__ import annotations

import time
from typing import Any, Callable, Iterable, Optional

import pyautogui


pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.03


class OpenAIComputerActionExecutor:
    """
    Ejecuta en el ordenador real las acciones devueltas por el tool `computer`
    de OpenAI.

    No hace llamadas a la API.
    No captura screenshots.
    Solo ejecuta acciones.

    Uso típico:
        executor = OpenAIComputerActionExecutor()

        # Si tienes el computer_call completo:
        result = executor.execute_computer_call(computer_call_dict)

        # Si ya tienes solo la lista actions:
        result = executor.execute_actions(actions_list)
    """

    def __init__(
        self,
        action_delay_seconds: float = 0.06,
        typing_interval_seconds: float = 0.0,
        default_wait_seconds: float = 1.5,
        on_before_action: Optional[Callable[[dict], bool]] = None,
        on_after_action: Optional[Callable[[dict, dict], None]] = None,
    ) -> None:
        """
        Args:
            action_delay_seconds:
                Pausa pequeña entre acciones.
            typing_interval_seconds:
                Intervalo entre caracteres al escribir.
            default_wait_seconds:
                Tiempo por defecto para la acción `wait` si no trae segundos.
            on_before_action:
                Callback opcional: fn(action_dict) -> bool
                Si devuelve False, la acción no se ejecuta.
            on_after_action:
                Callback opcional: fn(action_dict, result_dict) -> None
        """
        self.action_delay_seconds = action_delay_seconds
        self.typing_interval_seconds = typing_interval_seconds
        self.default_wait_seconds = default_wait_seconds
        self.on_before_action = on_before_action
        self.on_after_action = on_after_action

    # =========================================================
    # API pública
    # =========================================================

    def execute_computer_call(self, computer_call: dict[str, Any]) -> dict[str, Any]:
        """
        Recibe el objeto `computer_call` completo y ejecuta su array `actions`.

        Espera algo parecido a:
        {
            "type": "computer_call",
            "call_id": "...",
            "actions": [...]
        }
        """
        call_id = computer_call.get("call_id")
        actions = computer_call.get("actions", [])

        executed = self.execute_actions(actions)

        return {
            "call_id": call_id,
            "count": len(executed),
            "results": executed,
        }

    def execute_actions(self, actions: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Ejecuta una lista de acciones en orden.
        """
        results: list[dict[str, Any]] = []

        for action in actions:
            action = dict(action)

            if self.on_before_action is not None:
                allowed = self.on_before_action(action)
                if allowed is False:
                    result = {
                        "ok": False,
                        "type": action.get("type"),
                        "skipped": True,
                        "detail": "Acción bloqueada por on_before_action",
                    }
                    results.append({"action": action, "result": result})
                    if self.on_after_action is not None:
                        self.on_after_action(action, result)
                    continue

            try:
                result = self._execute_single_action(action)
            except Exception as e:
                result = {
                    "ok": False,
                    "type": action.get("type"),
                    "detail": f"{type(e).__name__}: {e}",
                }

            results.append({"action": action, "result": result})

            if self.on_after_action is not None:
                self.on_after_action(action, result)

            time.sleep(self.action_delay_seconds)

        return results

    # =========================================================
    # Ejecución interna
    # =========================================================

    def _execute_single_action(self, action: dict[str, Any]) -> dict[str, Any]:
        action_type = action.get("type")
        if not action_type:
            raise ValueError("La acción no tiene campo 'type'")

        if action_type == "click":
            self._action_click(action)
        elif action_type == "double_click":
            self._action_double_click(action)
        elif action_type == "scroll":
            self._action_scroll(action)
        elif action_type == "type":
            self._action_type(action)
        elif action_type == "wait":
            self._action_wait(action)
        elif action_type == "keypress":
            self._action_keypress(action)
        elif action_type == "drag":
            self._action_drag(action)
        elif action_type == "move":
            self._action_move(action)
        elif action_type == "screenshot":
            # No hace nada aquí. La captura la gestionas tú fuera.
            return {
                "ok": True,
                "type": action_type,
                "detail": "Acción screenshot ignorada por el ejecutor local",
            }
        else:
            raise ValueError(f"Tipo de acción no soportado: {action_type}")

        return {
            "ok": True,
            "type": action_type,
            "detail": "OK",
        }

    # =========================================================
    # Acciones
    # =========================================================

    def _action_click(self, action: dict[str, Any]) -> None:
        x = self._require_int(action, "x")
        y = self._require_int(action, "y")
        button = self._normalize_button(action.get("button", "left"))
        keys = self._normalize_keys(action.get("keys", []))

        def run():
            pyautogui.click(x=x, y=y, button=button)

        self._with_held_keys(keys, run)

    def _action_double_click(self, action: dict[str, Any]) -> None:
        x = self._require_int(action, "x")
        y = self._require_int(action, "y")
        button = self._normalize_button(action.get("button", "left"))
        keys = self._normalize_keys(action.get("keys", []))

        def run():
            pyautogui.doubleClick(x=x, y=y, button=button)

        self._with_held_keys(keys, run)

    def _action_move(self, action: dict[str, Any]) -> None:
        x = self._require_int(action, "x")
        y = self._require_int(action, "y")
        keys = self._normalize_keys(action.get("keys", []))

        def run():
            pyautogui.moveTo(x, y)

        self._with_held_keys(keys, run)

    def _action_drag(self, action: dict[str, Any]) -> None:
        keys = self._normalize_keys(action.get("keys", []))
        button = self._normalize_button(action.get("button", "left"))

        # Soporta varios formatos frecuentes
        if all(k in action for k in ("from_x", "from_y", "to_x", "to_y")):
            from_x = int(action["from_x"])
            from_y = int(action["from_y"])
            to_x = int(action["to_x"])
            to_y = int(action["to_y"])
        elif all(k in action for k in ("x", "y", "end_x", "end_y")):
            from_x = int(action["x"])
            from_y = int(action["y"])
            to_x = int(action["end_x"])
            to_y = int(action["end_y"])
        else:
            raise ValueError(
                "drag requiere from_x/from_y/to_x/to_y o x/y/end_x/end_y"
            )

        def run():
            pyautogui.moveTo(from_x, from_y)
            pyautogui.dragTo(to_x, to_y, button=button, duration=0.15)

        self._with_held_keys(keys, run)

    def _action_scroll(self, action: dict[str, Any]) -> None:
        x = action.get("x")
        y = action.get("y")
        keys = self._normalize_keys(action.get("keys", []))

        vertical = (
            action.get("scroll_y")
            if action.get("scroll_y") is not None
            else action.get("delta_y")
        )
        horizontal = (
            action.get("scroll_x")
            if action.get("scroll_x") is not None
            else action.get("delta_x")
        )

        if vertical is None:
            vertical = action.get("dy", 0)
        if horizontal is None:
            horizontal = action.get("dx", 0)

        vertical = int(vertical or 0)
        horizontal = int(horizontal or 0)

        def run():
            if x is not None and y is not None:
                pyautogui.moveTo(int(x), int(y))

            if vertical != 0:
                pyautogui.scroll(vertical)

            if horizontal != 0 and hasattr(pyautogui, "hscroll"):
                pyautogui.hscroll(horizontal)

        self._with_held_keys(keys, run)

    def _action_type(self, action: dict[str, Any]) -> None:
        text = action.get("text")
        if not isinstance(text, str):
            raise ValueError("type requiere un campo 'text' string")
        pyautogui.write(text, interval=self.typing_interval_seconds)

    def _action_wait(self, action: dict[str, Any]) -> None:
        seconds = action.get("seconds", self.default_wait_seconds)
        time.sleep(float(seconds))

    def _action_keypress(self, action: dict[str, Any]) -> None:
        """
        Soporta:
            {"type":"keypress","keys":["CTRL","L"]}
            {"type":"keypress","key":"ENTER"}
        """
        keys = action.get("keys")
        if not keys:
            key = action.get("key")
            if key:
                keys = [key]

        if not keys:
            raise ValueError("keypress requiere 'keys' o 'key'")

        normalized = self._normalize_keys(keys)

        if len(normalized) == 1:
            pyautogui.press(normalized[0])
        else:
            pyautogui.hotkey(*normalized)

    # =========================================================
    # Helpers
    # =========================================================

    def _with_held_keys(self, keys: list[str], fn) -> None:
        for key in keys:
            pyautogui.keyDown(key)
        try:
            fn()
        finally:
            for key in reversed(keys):
                pyautogui.keyUp(key)

    def _normalize_keys(self, keys: Any) -> list[str]:
        if keys is None:
            return []
        if not isinstance(keys, (list, tuple)):
            keys = [keys]
        return [self._normalize_key(k) for k in keys]

    def _normalize_key(self, key: str) -> str:
        if not key:
            raise ValueError("Tecla vacía")

        k = str(key).strip().upper()

        mapping = {
            "CTRL": "ctrl",
            "CONTROL": "ctrl",
            "ALT": "alt",
            "SHIFT": "shift",
            "META": "win",
            "SUPER": "win",
            "CMD": "win",
            "COMMAND": "win",
            "WINDOWS": "win",
            "ENTER": "enter",
            "RETURN": "enter",
            "ESC": "esc",
            "ESCAPE": "esc",
            "SPACE": "space",
            "TAB": "tab",
            "BACKSPACE": "backspace",
            "DELETE": "delete",
            "DEL": "delete",
            "INSERT": "insert",
            "HOME": "home",
            "END": "end",
            "PAGEUP": "pageup",
            "PAGEDOWN": "pagedown",
            "ARROWUP": "up",
            "ARROWDOWN": "down",
            "ARROWLEFT": "left",
            "ARROWRIGHT": "right",
            "UP": "up",
            "DOWN": "down",
            "LEFT": "left",
            "RIGHT": "right",
            "CAPSLOCK": "capslock",
            "PRINTSCREEN": "printscreen",
        }

        if k in mapping:
            return mapping[k]

        if len(k) == 1:
            return k.lower()

        if k.startswith("F") and k[1:].isdigit():
            return k.lower()

        return k.lower()

    def _normalize_button(self, button: Any) -> str:
        b = str(button or "left").strip().lower()
        if b not in ("left", "right", "middle"):
            return "left"
        return b

    def _require_int(self, data: dict[str, Any], key: str) -> int:
        if key not in data:
            raise ValueError(f"Falta campo requerido: {key}")
        return int(data[key])