import json
from pathlib import Path

SCHEMA = {"characters": [], "locations": []}

def new_empty_project():
    # tom mall enligt artefakt
    return {"characters": [], "locations": []}

def load_project(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    # minimal “schema merge” för att säkra nycklar
    return {**SCHEMA, **data}

def save_project(path: Path, data: dict) -> None:
    # enkel sanity: tvinga rätt nycklar
    payload = {
        "characters": data.get("characters", []),
        "locations": data.get("locations", []),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
