from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .validation import ARTIFACT_MODELS


def schema_names() -> list[str]:
    return sorted(ARTIFACT_MODELS)


def export_schema(name: str) -> dict[str, Any]:
    model = ARTIFACT_MODELS[name]
    return model.model_json_schema(by_alias=True)


def export_schemas(output_dir: str | Path) -> list[Path]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name in schema_names():
        path = target / f"{name}.schema.json"
        path.write_text(
            json.dumps(export_schema(name), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return written

