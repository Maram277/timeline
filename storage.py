import json, time
from pathlib import Path
from models import EMPTY, Project

def new_empty_project() -> Project:
    return {"characters": [], "locations": [], "events": []}

def load_project(path: Path) -> Project:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {**EMPTY, **data}

def save_project(path: Path, data: Project) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    # backup
    backups = path.parent / "backups"
    backups.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (backups / f"{path.stem}-{stamp}.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

def autosave(path: Path | None, data: Project):
    # fallback till hemkatalogen om projektet inte har sparats än
    target = path if path else Path.home() / ".timeline_autosave.json"
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
