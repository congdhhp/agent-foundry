# Threat-to-Control Matrix

| Threat | Controls | Required tests |
|---|---|---|
| Prompt injection | Untrusted content tagging, instruction isolation, policy-before-tool-call | Injection eval |
| Tool misuse | Risk levels, policy gate, approvals, audit | Forbidden tool eval |
| Secret leakage | Secret scanner, redaction, output verifier | Secret leak eval |
| PII leakage | PII classifier, redaction obligations, model policy | PII leak eval |
| Malicious skill | Skill review, checksum/signing, sandboxed scripts, evals | Skill supply-chain test |
| Malicious hook | Hook review, sandbox, allowlist, trust levels | Hook safety eval |
| Malicious extension | Extension scan, manifest review, commit pinning, checksum | Extension trust eval |
| Unsafe shell execution | Sandbox, allowlist, timeout, approval | Shell safety eval |
| Evidence fabrication | Evidence IDs, raw_ref, verifier, claim mapping | Claim-evidence eval |
| Cross-scope retrieval | ACL-aware retrieval, knowledge scopes | ACL eval |
| Cross-scope memory | Memory scopes, retention, access checks | Memory isolation test |
| Audit bypass | Append-only events, policy decision IDs | Audit completeness test |
| Excessive agency | Action budget, approval, side-effect classification | Agency limit eval |
