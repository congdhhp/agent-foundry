# Tool Security

Tools should support:

```text
authn/authz
input validation
output sanitization
rate limiting
network egress control
audit logging
risk classification
approval policy
secret redaction
PII redaction
sandboxing for execute tools
```

## Risk defaults

| Risk | Default behavior |
|---|---|
| Low | allow if authorized |
| Medium | allow with audit/redaction or approval |
| High | approval + sandbox |
| Critical | strong approval or deny |
