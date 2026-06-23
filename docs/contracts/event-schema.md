# Runtime Event Schema

```json
{
  "event_id": "evt_123",
  "event_type": "tool.executed",
  "timestamp": "2026-06-22T10:00:00Z",
  "trace_id": "trace_abc",
  "task_id": "task_456",
  "agent_id": "incident-triage-agent",
  "agent_revision": "rev-005",
  "snapshot_id": "snap_123",
  "node_id": "collect_logs",
  "payload": {
    "tool": "logs.search",
    "status": "success",
    "latency_ms": 842,
    "evidence_id": "ev_789"
  }
}
```
