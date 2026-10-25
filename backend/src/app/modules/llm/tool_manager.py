from pathlib import Path
import json
from typing import Any


class ToolManager:
    BASE_PATH = Path("data/tools")

    @classmethod
    def load(cls, name: str) -> Any:
        """
        Carga una tool desde data/tools/{name}.json
        y devuelve el JSON parseado.
        """
        path = cls.BASE_PATH / f"{name}.json"

        if not path.exists():
            raise FileNotFoundError(f"Tool '{name}' no encontrada en {path}")

        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"El archivo de tool '{name}' no contiene JSON válido: {path}") from e