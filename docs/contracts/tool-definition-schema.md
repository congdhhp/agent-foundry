# Tool Definition Schema

```yaml
id: string
name: string
description: string
provider: string
accessType: read | write | execute
riskLevel: low | medium | high | critical
inputSchema: object
outputSchema: object
createsEvidence: boolean
requiresApproval: boolean
actionType: optional string
whenToUse: string[]
whenNotToUse: string[]
examples: object[]
failureModes: string[]
```
