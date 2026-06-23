from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel

from agent_foundry.core.models import AgentState, Evidence, ResolvedAgentSnapshot, RuntimeEvent


class LocalStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def session_dir(self, task_id: str) -> Path:
        path = self.root / "sessions" / task_id
        path.mkdir(parents=True, exist_ok=True)
        (path / "artifacts").mkdir(exist_ok=True)
        return path

    def write_state(self, state: AgentState) -> None:
        self._write_model(self.session_dir(state.taskId) / "state.json", state)

    def write_snapshot(self, task_id: str, snapshot: ResolvedAgentSnapshot) -> None:
        self._write_model(self.session_dir(task_id) / "snapshot.json", snapshot)

    def append_event(self, event: RuntimeEvent) -> None:
        self._append_model(self.session_dir(event.task_id) / "events.jsonl", event)

    def append_evidence(self, evidence: Evidence) -> None:
        self._append_model(self.session_dir(evidence.task_id) / "evidence.jsonl", evidence)

    def read_events(self, task_id: str) -> list[dict]:
        return self._read_jsonl(self.session_dir(task_id) / "events.jsonl")

    def read_evidence(self, task_id: str) -> list[dict]:
        return self._read_jsonl(self.session_dir(task_id) / "evidence.jsonl")

    def list_sessions(self) -> Iterable[Path]:
        sessions = self.root / "sessions"
        if not sessions.exists():
            return []
        return sorted((path for path in sessions.iterdir() if path.is_dir()), key=lambda path: path.name)

    def _write_model(self, path: Path, model: BaseModel) -> None:
        path.write_text(model.model_dump_json(indent=2), encoding="utf-8")

    def _append_model(self, path: Path, model: BaseModel) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(model.model_dump_json())
            handle.write("\n")

    def _read_jsonl(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]
