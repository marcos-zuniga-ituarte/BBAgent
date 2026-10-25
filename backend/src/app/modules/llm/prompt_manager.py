from pathlib import Path


class PromptManager:

    BASE_PATH = Path("data/prompts")

    @classmethod
    def load(cls, name: str) -> str:
        """
        Carga un prompt desde data/prompts/{name}.txt
        """
        path = cls.BASE_PATH / f"{name}.txt"

        if not path.exists():
            raise FileNotFoundError(f"Prompt '{name}' no encontrado en {path}")

        return path.read_text(encoding="utf-8")