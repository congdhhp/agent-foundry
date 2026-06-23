# Policy Decision Schema

```json
{
  "decision_id": "pol_123",
  "task_id": "task_456",
  "tool_call_id": "tool_call_789",
  "tool": "message.send",
  "action_type": "message.send",
  "decision": "REQUIRE_APPROVAL",
  "reason": "Sending external message is a side-effect action.",
  "obligations": [
    "create_audit_event",
    "attach_evidence_summary"
  ]
}
```

## Decisions

```text
ALLOW
DENY
REQUIRE_APPROVAL
REQUIRE_TRANSFORM
REQUIRE_STEP_UP_AUTH
```
