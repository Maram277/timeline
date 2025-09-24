import json
from pathlib import Path

SCHEMA = {"characters": [], "locations": []}

def new_empty_project() -> dict:
    return {"characters": [], "locations": []}

def load_project(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {**SCHEMA, **data}

def save_project(path: Path, data: dict) -> None:
    payload = {
        "characters": data.get("characters", []),
        "locations": data.get("locations", []),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
