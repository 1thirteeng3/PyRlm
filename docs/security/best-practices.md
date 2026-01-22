# Security Best Practices

Guidelines for deploying RLM securely in production.

## Deployment Checklist

- [ ] Docker is running with security updates
- [ ] gVisor (runsc) is installed if on Linux
- [ ] Network isolation is enabled (`RLM_NETWORK_ENABLED=false`)
- [ ] Memory limits are configured
- [ ] API keys are stored securely (not in code)
- [ ] Budget limits are set appropriately
- [ ] Egress filtering thresholds are reviewed

## API Key Security

### ❌ Don't

```python
# Never hardcode keys
client = OpenAIClient(api_key="sk-abc123...")
```

### ✅ Do

```python
# Use environment variables
from rlm import settings
# RLM_API_KEY loaded from .env or environment
```

### Recommended: Use Secrets Managers

```python
import os
from azure.keyvault.secrets import SecretClient

# Load from Azure Key Vault
secret = keyvault_client.get_secret("rlm-api-key")
os.environ["RLM_API_KEY"] = secret.value
```

## Docker Hardening

### Use Minimal Base Images

```bash
RLM_DOCKER_IMAGE=python:3.11-slim  # Good
# Avoid: python:3.11  # Larger attack surface
```

### Pre-install Dependencies

Since network is disabled, all dependencies must be in the image:

```dockerfile
# Custom sandbox image
FROM python:3.11-slim

RUN pip install --no-cache-dir \
    numpy pandas scipy scikit-learn

# No network access at runtime
```

### Keep Images Updated

```bash
docker pull python:3.11-slim
# Regularly update for security patches
```

## Network Considerations

### Never Enable Network in Production

```bash
RLM_NETWORK_ENABLED=false  # Must be false
```

If you need external data:
1. Pre-fetch data before execution
2. Mount as read-only volume
3. Use `ContextHandle` for access

## Logging and Auditing

Log all orchestrator executions:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rlm")

# Logs will include:
# - Code executed
# - Execution results
# - Egress filter actions
# - Cost tracking
```

## Rate Limiting

Protect against abuse:

```python
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_requests=10, window=timedelta(minutes=1)):
        self.requests = []
        self.max = max_requests
        self.window = window
    
    def check(self):
        now = datetime.now()
        self.requests = [r for r in self.requests if now - r < self.window]
        if len(self.requests) >= self.max:
            raise RateLimitError("Too many requests")
        self.requests.append(now)
```

## Budget Protection

Set conservative limits:

```bash
RLM_COST_LIMIT_USD=5.0  # Per session
RLM_MAX_RECURSION_DEPTH=5  # Prevent infinite loops
```

## Monitoring

Track these metrics:

- Execution count per hour
- Average cost per execution
- Egress filter triggers
- Container OOM kills
- Security test failures

## Incident Response

If a security issue is detected:

1. **Immediately** revoke API keys
2. **Review** execution logs
3. **Check** for data exfiltration attempts
4. **Update** egress filter patterns
5. **Rotate** all credentials
