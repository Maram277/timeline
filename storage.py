import json
from pathlib import Path

SCHEMA = {"characters": [], "locations": [], "events": []}

def new_empty_project() -> dict:
    return {"characters": [], "locations": [], "events": []}

def load_project(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {**SCHEMA, **data}

def save_project(path: Path | None, data: dict) -> None:
    if path is None:
        raise ValueError("No file path selected. Use 'Save As…' first.")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
