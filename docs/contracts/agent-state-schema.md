# AgentState Schema

```ts
type AgentState = {
  taskId: string
  traceId: string
  agentId: string
  agentRevision: string
  snapshotId: string
  userId?: string
  tenantId?: string

  input: string
  metadata: Record<string, unknown>

  resolvedSnapshot: ResolvedAgentSnapshot
  resolvedContext: ResolvedContext

  messages: RuntimeMessage[]
  plan: PlannedStep[]
  proposedToolCalls: ProposedToolCall[]
  policyDecisions: PolicyDecision[]
  hookResults: HookResult[]
  toolCalls: ToolCallRecord[]
  approvals: ApprovalRecord[]

  observations: Observation[]
  evidence: Evidence[]
  draftOutput?: unknown
  finalOutput?: unknown

  verificationResults: VerificationResult[]
  evalResults?: EvalResult[]
}
```
