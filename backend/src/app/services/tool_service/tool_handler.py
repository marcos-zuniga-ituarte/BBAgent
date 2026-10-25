from typing import Protocol, Dict, Any


class ToolHandler(Protocol):
    name: str

    def execute(self) -> Dict[str, Any]:
        ...