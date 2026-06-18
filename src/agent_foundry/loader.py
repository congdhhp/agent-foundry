from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def load_document(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    suffix = file_path.suffix.lower()
    if suffix == ".json":
        loaded = json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        loaded = yaml.safe_load(text)
    else:
        raise ValueError(f"Unsupported artifact file extension: {file_path.suffix}")
    if not isinstance(loaded, dict):
        raise ValueError(f"Artifact file must contain an object: {file_path}")
    return loaded


def dump_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, default=str)


def dump_yaml(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)

