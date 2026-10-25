from __future__ import annotations

import json
from io import BytesIO
from typing import Iterable, List, Dict, Type, Any
from openai import OpenAI
from pydantic import BaseModel

from app.data_access import Message


class LLM:
    def __init__(self) -> None:
        self.client = OpenAI()

    def generate(self,
                 model: str,
                 instructions: List[Dict],
                 messages: List[Dict]) -> str:

        response = self.client.responses.create(
            model=model,
            input=instructions + messages,
            reasoning={"effort": "low"},
        )

        return response.output_text

    def stream(self,
               model: str,
               instructions: List[Dict],
               messages: List[Dict]) -> Iterable[str]:

        with self.client.responses.stream(
                model=model,
                input=instructions + messages,
                reasoning={"effort": "low"},
        ) as stream:
            for event in stream:
                if event.type == "response.output_text.delta":
                    if event.delta:
                        yield event.delta

    from typing import List, Dict, Any

    def tools_call(self,
                   model: str,
                   instructions: List[Dict],
                   messages: List[Dict],
                   tools: List[Dict]) -> List[Dict[str, Any]]:

        response = self.client.responses.create(
            model=model,
            input=instructions + messages,
            tools=tools,
            reasoning={"effort": "low"},
            # tool_choice="required"
        )
        return response.output

    def tools_call_stream(self, model, instructions, messages, tools):
        stream = self.client.responses.create(
            model=model,
            input=instructions + messages,
            tools=tools,
            stream=True,
            reasoning={"effort": "none"},
            # include=["reasoning.encrypted_content"],
            # store=False,  # opcional si quieres forzar modo stateless
        )

        partial_tool_calls = {}

        for event in stream:
            if event.type == "response.output_text.delta":
                yield {
                    "type": "token",
                    "value": event.delta,
                }

            elif event.type == "response.output_item.added":
                item_type = getattr(event.item, "type", None)

                if item_type == "function_call":
                    partial_tool_calls[event.output_index] = event.item

            elif event.type == "response.function_call_arguments.delta":
                index = event.output_index
                if index in partial_tool_calls:
                    partial_tool_calls[index].arguments += event.delta

            elif event.type == "response.function_call_arguments.done":
                index = event.output_index
                tool_call = partial_tool_calls.get(index)

                if tool_call is not None:
                    yield {
                        "type": "function_call",
                        "id": tool_call.id,
                        "call_id": tool_call.call_id,
                        "name": tool_call.name,
                        "arguments": json.loads(event.arguments),

                    }
                    del partial_tool_calls[index]
            elif event.type == "response.completed":
                # IMPORTANTE:
                # aquí devolvemos TODOS los output items completos
                # para poder reconstruir el contexto manualmente
                yield {
                    "type": "response_items",
                    "value": [item.model_dump() for item in event.response.output],
                }

    def speech_to_text(
            self,
            model: str,
            audio_bytes: bytes,
            filename: str,
            known_voices = None,
    ) -> str:
        audio_buffer = BytesIO(audio_bytes)
        audio_buffer.name = filename  # importante para que detecte el formato

        transcript = self.client.audio.transcriptions.create(
            model=model,
            file=audio_buffer,
            response_format="diarized_json",
            chunking_strategy="auto",
            extra_body=known_voices,
        )

        return transcript.text

    def add_files(self, files: list[dict]) -> list[str]:
        file_ids = []

        for file in files:
            filename = file["filename"]
            file_bytes = file["bytes"]
            mime_type = file.get("mime_type", "application/octet-stream")

            uploaded = self.client.files.create(
                file=(filename, file_bytes, mime_type),
                purpose="user_data",
            )

            file_ids.append(uploaded.id)

        return file_ids

    def _serialize_compacted_item(self, item) -> dict | None:
        item_type = getattr(item, "type", None)

        if item_type == "compaction":
            return {
                "type": "compaction",
                "encrypted_content": item.encrypted_content,
            }

        if item_type == "message":
            content_parts = []

            for part in getattr(item, "content", []) or []:
                part_type = getattr(part, "type", None)

                if part_type in {"input_text", "output_text", "text"}:
                    text = getattr(part, "text", None)
                    if text is not None:
                        content_parts.append({
                            "type": part_type,
                            "text": text,
                        })

                elif part_type == "input_image":
                    entry = {
                        "type": "input_image",
                        "image_url": getattr(part, "image_url", None),
                    }
                    detail = getattr(part, "detail", None)
                    if detail is not None:
                        entry["detail"] = detail
                    content_parts.append(entry)

                elif part_type == "input_file":
                    entry = {"type": "input_file"}
                    for field in ("filename", "file_id", "file_data"):
                        value = getattr(part, field, None)
                        if value is not None:
                            entry[field] = value
                    content_parts.append(entry)

            return {
                "type": "message",
                "role": getattr(item, "role", "user"),
                "content": content_parts,
            }

        return None

    def compact_conversation(
            self,
            model: str,
            messages: List[Dict],
    ) -> List[Dict[str, Any]]:
        compacted = self.client.responses.compact(
            model=model,
            input=messages,
        )

        sanitized_items: List[Dict[str, Any]] = []

        for item in compacted.output:
            serialized = self._serialize_compacted_item(item)
            if serialized is not None:
                sanitized_items.append(serialized)

        return sanitized_items

    def structured(
            self,
            model: str,
            instructions: List[Dict],
            messages: List[Dict],
            schema: Type[BaseModel],
    ) -> Dict[str, Any]:

        response = self.client.responses.parse(
            model=model,
            input=instructions + messages,
            text_format=schema,
        )

        parsed = response.output_parsed

        if parsed is None:
            raise ValueError("Structured response parsing failed.")

        # devolver dict limpio
        return parsed.model_dump(mode="json")


llm = LLM()
