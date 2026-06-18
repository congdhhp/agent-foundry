from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def new_task_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"task_{timestamp}_{uuid4().hex[:8]}"


class LocalSessionStore:
    def __init__(self, root: str | Path = ".agent") -> None:
        self.root = Path(root)
        self.sessions_dir = self.root / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def create_session(self, task_id: str) -> Path:
        session_dir = self.session_dir(task_id)
        (session_dir / "artifacts").mkdir(parents=True, exist_ok=True)
        self._ensure_checkpoint_db(task_id)
        return session_dir

    def session_dir(self, task_id: str) -> Path:
        return self.sessions_dir / task_id

    def append_event(self, task_id: str, event_type: str, payload: dict[str, Any]) -> None:
        event = {
            "event_type": event_type,
            "task_id": task_id,
            "timestamp": utc_now(),
            "payload": payload,
        }
        self._append_jsonl(task_id, "events.jsonl", event)

    def append_trace(self, task_id: str, payload: dict[str, Any]) -> None:
        trace = {"task_id": task_id, "timestamp": utc_now(), **payload}
        self._append_jsonl(task_id, "trace.jsonl", trace)

    def append_evidence(self, task_id: str, evidence: dict[str, Any]) -> None:
        self._append_jsonl(task_id, "evidence.jsonl", evidence)

    def append_approval(self, task_id: str, approval: dict[str, Any]) -> None:
        self._append_jsonl(task_id, "approvals.jsonl", approval)

    def save_artifact(self, task_id: str, name: str, data: dict[str, Any]) -> Path:
        path = self.session_dir(task_id) / "artifacts" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def save_checkpoint(
        self,
        task_id: str,
        workflow_id: str,
        node_id: str,
        state: dict[str, Any],
        status: str,
    ) -> str:
        checkpoint_id = f"ckpt_{uuid4().hex[:12]}"
        conn = sqlite3.connect(self.session_dir(task_id) / "checkpoints.sqlite")
        try:
            conn.execute(
                """
                insert into checkpoints (
                    id, task_id, workflow_id, node_id, state_json, status, created_at
                )
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    checkpoint_id,
                    task_id,
                    workflow_id,
                    node_id,
                    json.dumps(state, sort_keys=True, default=str),
                    status,
                    utc_now(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return checkpoint_id

    def list_sessions(self) -> list[dict[str, Any]]:
        sessions: list[dict[str, Any]] = []
        for path in sorted(self.sessions_dir.glob("task_*")):
            final_path = path / "artifacts" / "final_response.json"
            summary: dict[str, Any] = {"task_id": path.name, "status": "unknown"}
            if final_path.exists():
                summary.update(json.loads(final_path.read_text(encoding="utf-8")))
            sessions.append(summary)
        return sessions

    def read_jsonl(self, task_id: str, name: str) -> list[dict[str, Any]]:
        path = self.session_dir(task_id) / name
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _append_jsonl(self, task_id: str, name: str, record: dict[str, Any]) -> None:
        session_dir = self.create_session(task_id)
        path = session_dir / name
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, sort_keys=True, default=str) + "\n")

    def _ensure_checkpoint_db(self, task_id: str) -> None:
        db_path = self.session_dir(task_id) / "checkpoints.sqlite"
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                """
                create table if not exists checkpoints (
                    id text primary key,
                    task_id text not null,
                    workflow_id text not null,
                    node_id text not null,
                    state_json text not null,
                    status text not null,
                    created_at text not null
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

