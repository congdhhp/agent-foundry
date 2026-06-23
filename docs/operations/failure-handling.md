# Failure Handling

## Failure categories

```text
tool timeout
tool error
invalid tool output
policy denial
approval rejection
approval timeout
user cancellation
model failure
rate limit
partial evidence
verifier failure
eval failure
checkpoint failure
hook failure
context resolution failure
memory read/write failure
snapshot resolution failure
```

## Graceful degradation

When a needed source/tool is unavailable:

```text
state what is unavailable
continue with available evidence if safe
lower confidence
avoid unsupported conclusions
recommend next data needed
record failure in audit/trace
```
