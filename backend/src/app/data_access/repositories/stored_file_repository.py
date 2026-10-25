from typing import Optional, Any

from sqlalchemy import select, func

from app.data_access.db import _DatabaseManager
from app.data_access.models.stored_file import StoredFile
from app.data_access.utils import utc_now


class StoredFileRepository:

    @staticmethod
    def create(
        user_id: str,
        filename: str,
        mime_type: str,
        data: bytes,
        chat_id: str | None = None,
        message_id: str | None = None,
        position: int | None = None,
        aux_file_id: str | None = None,
    ) -> StoredFile:
        cleaned_filename = filename.strip()
        cleaned_mime_type = (mime_type or "application/octet-stream").strip()

        if not user_id:
            raise ValueError("user_id cannot be empty.")

        if not cleaned_filename:
            raise ValueError("filename cannot be empty.")

        if not cleaned_mime_type:
            raise ValueError("mime_type cannot be empty.")

        if data is None:
            raise ValueError("data cannot be None.")

        size_bytes = len(data)

        stored_file = StoredFile(
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            position=position,
            aux_file_id=aux_file_id,
            filename=cleaned_filename,
            mime_type=cleaned_mime_type,
            size_bytes=size_bytes,
            data=data,
            created_at=utc_now(),
        )

        with _DatabaseManager.session() as session:
            session.add(stored_file)
            session.commit()
            session.refresh(stored_file)

        return stored_file

    @staticmethod
    def get_by_id(file_id: str) -> Optional[StoredFile]:
        with _DatabaseManager.session() as session:
            return session.get(StoredFile, file_id)

    @staticmethod
    def get_by_message(message_id: str) -> list[StoredFile]:
        with _DatabaseManager.session() as session:
            stmt = (
                select(StoredFile)
                .filter_by(message_id=message_id)
                .order_by(StoredFile.position.asc(), StoredFile.created_at.asc())
            )
            return list(session.scalars(stmt).all())

    @staticmethod
    def delete(file_id: str) -> None:
        with _DatabaseManager.session() as session:
            stored_file = session.get(StoredFile, file_id)
            if stored_file:
                session.delete(stored_file)
                session.commit()

    @staticmethod
    def create_for_message(
            message_id: str,
            chat_id: str,
            filename: str,
            mime_type: str,
            data: bytes,
            aux_file_id: str | None = None,
    ) -> StoredFile:
        from app.data_access.models.chat import Chat
        cleaned_filename = filename.strip()
        cleaned_mime_type = (mime_type or "application/octet-stream").strip()

        if not message_id:
            raise ValueError("message_id cannot be empty.")

        if not chat_id:
            raise ValueError("chat_id cannot be empty.")

        if not cleaned_filename:
            raise ValueError("filename cannot be empty.")

        if not cleaned_mime_type:
            raise ValueError("mime_type cannot be empty.")

        if data is None:
            raise ValueError("data cannot be None.")

        with _DatabaseManager.session() as session:
            db_chat = session.get(Chat, chat_id)
            if db_chat is None:
                raise ValueError(f"Chat with id {chat_id} does not exist.")

            stmt = select(func.max(StoredFile.position)).filter_by(message_id=message_id)
            max_position = session.execute(stmt).scalar_one_or_none()

            next_position = 0 if max_position is None else max_position + 1

            stored_file = StoredFile(
                user_id=db_chat.user_id,
                chat_id=chat_id,
                message_id=message_id,
                position=next_position,
                aux_file_id=aux_file_id,
                filename=cleaned_filename,
                mime_type=cleaned_mime_type,
                size_bytes=len(data),
                data=data,
                created_at=utc_now(),
            )

            session.add(stored_file)
            session.commit()
            session.refresh(stored_file)

            return stored_file

    @staticmethod
    def create_many_for_message(
            message_id: str,
            chat_id: str,
            files: list[dict],
    ) -> list[StoredFile]:
        from app.data_access.models.chat import Chat
        if not message_id:
            raise ValueError("message_id cannot be empty.")

        if not chat_id:
            raise ValueError("chat_id cannot be empty.")

        if not files:
            return []

        created_files: list[StoredFile] = []

        with _DatabaseManager.session() as session:
            db_chat = session.get(Chat, chat_id)
            if db_chat is None:
                raise ValueError(f"Chat with id {chat_id} does not exist.")

            stmt = select(func.max(StoredFile.position)).filter_by(message_id=message_id)
            max_position = session.execute(stmt).scalar_one_or_none()

            next_position = 0 if max_position is None else max_position + 1
            now = utc_now()

            for i, file in enumerate(files):
                filename = (file.get("filename") or "").strip()
                mime_type = (file.get("mime_type") or "application/octet-stream").strip()
                data = file.get("data")
                aux_file_id = file.get("aux_file_id")

                if not filename:
                    raise ValueError("filename cannot be empty.")

                if not mime_type:
                    raise ValueError("mime_type cannot be empty.")

                if data is None:
                    raise ValueError("data cannot be None.")

                stored_file = StoredFile(
                    user_id=db_chat.user_id,
                    chat_id=chat_id,
                    message_id=message_id,
                    position=next_position + i,
                    aux_file_id=aux_file_id,
                    filename=filename,
                    mime_type=mime_type,
                    size_bytes=len(data),
                    data=data,
                    created_at=now,
                )

                session.add(stored_file)
                created_files.append(stored_file)

            session.commit()

            for stored_file in created_files:
                session.refresh(stored_file)

            return created_files

    @staticmethod
    def get(
            user_id: str | None = None,
            chat_id: str | None = None,
            message_id: str | None = None,
    ) -> list[StoredFile]:
        with _DatabaseManager.session() as session:
            stmt = select(StoredFile)

            if user_id is not None:
                stmt = stmt.filter_by(user_id=user_id)

            if chat_id is not None:
                stmt = stmt.filter_by(chat_id=chat_id)

            if message_id is not None:
                stmt = stmt.filter_by(message_id=message_id)

            stmt = stmt.order_by(StoredFile.position.asc(), StoredFile.created_at.asc())

            return list(session.scalars(stmt).all())

    @staticmethod
    def create_many(
            user_id: str,
            files: list[dict[str, Any]],
            chat_id: str | None = None,
            message_id: str | None = None,
    ) -> list[StoredFile]:
        if not user_id:
            raise ValueError("user_id cannot be empty.")

        if not files:
            return []

        created_files: list[StoredFile] = []

        with _DatabaseManager.session() as session:
            base_position = None

            if message_id is not None:
                stmt = select(func.max(StoredFile.position)).filter_by(message_id=message_id)
                max_position = session.execute(stmt).scalar_one_or_none()
                base_position = 0 if max_position is None else max_position + 1

            now = utc_now()

            for i, file in enumerate(files):
                filename = (file.get("filename") or "").strip()
                mime_type = (file.get("mime_type") or "application/octet-stream").strip()
                data = file.get("data")
                aux_file_id = file.get("aux_file_id")

                if not filename:
                    raise ValueError("filename cannot be empty.")

                if not mime_type:
                    raise ValueError("mime_type cannot be empty.")

                if data is None:
                    raise ValueError("data cannot be None.")

                position = None if base_position is None else base_position + i

                stored_file = StoredFile(
                    user_id=user_id,
                    chat_id=chat_id,
                    message_id=message_id,
                    position=position,
                    aux_file_id=aux_file_id,
                    filename=filename,
                    mime_type=mime_type,
                    size_bytes=len(data),
                    data=data,
                    created_at=now,
                )

                session.add(stored_file)
                created_files.append(stored_file)

            session.commit()

            for stored_file in created_files:
                session.refresh(stored_file)

            return created_files