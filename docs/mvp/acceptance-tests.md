# MVP Acceptance Tests

```yaml
acceptanceTests:
  - id: blank_agent_can_be_created
    expect:
      - agent status is Draft
      - default runtime assigned
      - default safety policy assigned
      - no tools required
      - no skills required

  - id: guidance_file_loaded
    given: AGENTS.md exists
    expect:
      - guidance included in resolved context snapshot

  - id: skill_selection_works
    given: task "Investigate checkout 5xx spike after latest deploy"
    expect:
      - selectedSkill: incident-triage

  - id: tool_policy_gate_required
    given: proposed tool call logs.search
    expect:
      - policy decision exists before execution

  - id: policy_blocks_side_effect
    given: deployment.rollback proposed in prod
    expect:
      - rollback not executed
      - approval request created
      - audit event recorded

  - id: evidence_required_for_operational_claim
    given: final output claims likely cause
    expect:
      - claim has evidence_refs

  - id: revision_created_on_component_change
    when: tool logs.search is added
    expect:
      - new agent revision created

  - id: running_task_uses_immutable_snapshot
    when: agent definition changes during a task
    expect:
      - current task remains on original snapshot
      - new task uses new revision

  - id: imported_github_skill_untrusted_by_default
    when: skill imported from GitHub
    expect:
      - trustLevel: untrusted
      - scripts disabled by default
      - eval required before production
```
