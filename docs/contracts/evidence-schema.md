# Evidence Schema

```json
{
  "id": "ev_001",
  "task_id": "task_123",
  "trace_id": "trace_abc",
  "source_type": "tool_result",
  "source_uri": "metrics://checkout/5xx",
  "tool": "metrics.query",
  "summary": "5xx rate increased from 0.2% to 8.4% after deployment v1.2.3.",
  "raw_ref": "object://task_123/tool_result_456",
  "sensitivity": "internal",
  "confidence": 0.87,
  "created_at": "2026-06-22T10:00:00Z"
}
```
