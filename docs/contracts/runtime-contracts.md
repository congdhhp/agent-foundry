# Runtime Contracts

```ts
interface AgentRuntime {
  run(input: AgentRunInput): Promise<AgentRunResult>
  resume(taskId: string, decision: HumanDecision): Promise<AgentRunResult>
}

interface SnapshotResolver {
  resolve(agentId: string, revision?: string): Promise<ResolvedAgentSnapshot>
}

interface ContextResolver {
  resolve(input: ContextResolutionInput): Promise<ResolvedContext>
}

interface SkillSelector {
  select(input: SkillSelectionInput): Promise<SelectedSkill[]>
}

interface CommandResolver {
  resolve(command: string, context: RuntimeContext): Promise<ResolvedCommand>
}

interface PolicyEngine {
  evaluate(action: ProposedToolCall, context: PolicyContext): Promise<PolicyDecision>
}

interface ToolExecutor {
  execute(call: ApprovedToolCall): Promise<ToolResult>
}

interface HookRunner {
  run(event: HookEvent, context: HookContext): Promise<HookResult[]>
}

interface EvidenceManager {
  createFromToolResult(result: ToolResult): Promise<Evidence>
  createFromRetrieval(result: RetrievalResult): Promise<Evidence>
}

interface EvalRunner {
  run(profile: EvalProfile, agent: AgentDefinition): Promise<EvalRunResult>
}
```
