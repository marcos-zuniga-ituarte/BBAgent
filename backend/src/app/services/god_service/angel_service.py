import base64
import os
from datetime import timezone, datetime

from app.modules.llm.llm import llm
from app.modules.llm.prompt_manager import PromptManager
from app.data_access import User, Chat, Message
from app.services.brain_service.brain_service import BrainService
from app.services.god_service.angel_status import AngelStoppedException
from app.services.tool_service.tool_service import ToolService

model_terminal = os.getenv("OPENAI_AGENT_MODEL")
model_speech_to_text = os.environ.get("OPENAI_TRANSCRIPTION_MODEL")

prompt_terminal_prompt = os.getenv("AGENT_PROMPT")

title_length = int(os.environ.get("CHAT_TITLE_MAX_LENGTH"))




class Angel:

    def __init__(
            self,
            user: User,
            chat: Chat,
            sender,
            ask_for_confirmation: int,
            texto_usuario,
            system_prompt_list=None,
            audio_bytes: bytes | None = None,
            audio_filename: str | None = None,
            files: list[dict] | None = None,
    ):
        self.user = user
        self.chat = chat
        self.sender = sender
        self.ask_for_confirmation = ask_for_confirmation
        self.texto_usuario = texto_usuario
        self.system_prompt_list = system_prompt_list
        self.audio_bytes = audio_bytes
        self.audio_filename = audio_filename
        self.files = files or []

        self.created_at = None
        self.last_user_message_id = None

        self.tool_service = ToolService(
            user=self.user,
            chat=self.chat,
            sender=self.sender,
            ask_for_confirmation=self.ask_for_confirmation,
        )

    def get_id(self) -> str:
        return self.chat.id

    def execute(self) -> None:
        self.sender.reset_for_new_run()

        if self.audio_bytes is not None:
            self.sender.send_status("Transcribing audio")

            self.texto_usuario = llm.speech_to_text(
                model=model_speech_to_text,
                audio_bytes=self.audio_bytes,
                filename=self.audio_filename,
            )

        if not self.texto_usuario and not self.files:
            raise ValueError("No user text or files available")

        if len(self.chat.get_messages()) == 0 and self.texto_usuario:
            self.chat.change_title(self.texto_usuario[:title_length])

        terminal_instructions = [
            {"role": "developer", "content": PromptManager.load(prompt_terminal_prompt)}
        ]

        user_content = []
        ui_files = []

        if self.files:
            for f in self.files:
                filename = f.get("filename") or "archivo_sin_nombre"
                mime_type = f["mime_type"]
                file_bytes = f["bytes"]

                base64_data = base64.b64encode(file_bytes).decode("utf-8")

                if mime_type.startswith("image/"):
                    data_url = f"data:{mime_type};base64,{base64_data}"

                    # payload para OpenAI
                    user_content.append({
                        "type": "input_image",
                        "image_url": data_url,
                        "detail": "auto",
                    })

                    # payload para UI
                    ui_files.append({
                        "type": "image",
                        "image_url": data_url,
                    })

                else:
                    # payload para OpenAI
                    user_content.append({
                        "type": "input_file",
                        "filename": filename,
                        "file_data": f"data:{mime_type};base64,{base64_data}",
                    })

                    # payload para UI
                    ui_files.append({
                        "type": "file",
                        "filename": filename,
                    })

        if self.texto_usuario:
            user_content.append({
                "type": "input_text",
                "text": self.texto_usuario,
            })

        msg = self.chat.add_message({
            "role": "user",
            "content": user_content
        }, show=True)

        if self.files:
            msg.add_files([
                {
                    "filename": f.get("filename") or "archivo_sin_nombre",
                    "mime_type": f["mime_type"],
                    "data": f["bytes"],
                    "aux_file_id": None,
                }
                for f in self.files
            ])

        ui_content = {
            "text": self.texto_usuario or "",
            "files": ui_files,
        }

        self.sender.send_message({
            "id": msg.id,
            "role": "user",
            "content": ui_content,
        })

        self.last_user_message_id = msg.id

        self.created_at = datetime.now(timezone.utc).isoformat()
        respuesta = ""
        brain_service = BrainService(self.chat)
        brain_service.start()

        try:
            try:
                while True:

                    self.sender.send_status("Thinking")

                    tools = self.tool_service.get_tools()

                    user_instructions = []
                    user_prompt = getattr(self.user, "system_prompt", None)
                    if self.system_prompt_list == None:
                        self.system_prompt_list = terminal_instructions
                        if user_prompt:
                            self.system_prompt_list.append({
                                "role": "system",
                                "content": user_prompt.strip(),
                            })
                    result = llm.tools_call_stream(
                        model=model_terminal,
                        instructions=self.system_prompt_list + user_instructions,
                        messages=brain_service.get_context(),
                        tools=tools,
                    )

                    submitted_any_tool = False
                    respuesta = ""

                    for chunk in result:
                        if chunk["type"] == "token":
                            token = chunk["value"] or ""
                            respuesta += token
                            self.sender.send_token(token)

                        elif chunk["type"] == "function_call":

                            self.tool_service.submit_call(chunk)
                            submitted_any_tool = True
                    message_response = {
                        "role": "assistant",
                        "content": respuesta
                    }
                    brain_service.add_message(message_response, show=not (respuesta == ""))

                    self.sender.send_message_close()

                    if not submitted_any_tool:
                        break

                    tool_messages = self.tool_service.collect()
                    brain_service.add_messages(tool_messages)

            except AngelStoppedException as e:
                raise e
            finally:
                self.tool_service.shutdown()

            self.sender.send_status("Memory update")
            brain_service.wait_for_memory_update()

            self.sender.send_done()

        except AngelStoppedException:
            partial = (self.sender.partial_response or "").strip()

            msg = brain_service.add_message(
                {"role": Message.Role.ASSISTANT, "content": partial},
                show=True,
            )

            if partial != "":
                self.sender.send_message({
                    "id": msg.id,
                    "role": Message.Role.ASSISTANT,
                    "content": partial,
                })
            self.sender.send_status("Memory update")
            brain_service.wait_for_memory_update()

            self.sender.send_stopped()

        except Exception as e:
            self.sender.send_error(str(e))
            raise
