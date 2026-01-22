# Security Best Practices

Deploy RLM securely in production.

## The Golden Rules

!!! success "Always"
    - ✅ Use gVisor in production
    - ✅ Keep `RLM_NETWORK_ENABLED=0`
    - ✅ Set appropriate resource limits
    - ✅ Update Docker images regularly
    - ✅ Monitor execution logs

!!! danger "Never"
    - ❌ Use `allow_unsafe_runtime=True` in production
    - ❌ Enable network without strong justification
    - ❌ Run without resource limits
    - ❌ Ignore egress filter warnings

## Production Configuration

```bash
# Strict security settings
export RLM_DOCKER_RUNTIME=runsc        # Force gVisor
export RLM_ALLOW_UNSAFE_RUNTIME=0      # Fail if no gVisor
export RLM_NETWORK_ENABLED=0           # No network
export RLM_MEMORY_LIMIT=128m           # Tight limits
export RLM_CPU_LIMIT=0.25              # Minimal CPU
export RLM_EXECUTION_TIMEOUT=15        # Short timeout
export RLM_PIDS_LIMIT=30               # Limit processes
```

## Docker Hardening

### Use Minimal Images

```dockerfile
# ✅ Good: Minimal base
FROM python:3.11-slim

# ❌ Bad: Full base with unnecessary tools
FROM python:3.11
```

### Regular Updates

```bash
# Update weekly
docker pull python:3.11-slim
```

### Read-Only Root

RLM already mounts volumes as read-only, but you can add:

```python
# In SandboxConfig
read_only=True  # Make container filesystem read-only
```

## Egress Filtering Tuning

### Raise on Leak

In production, you may want to **fail** instead of redact:

```python
from rlm.core import OrchestratorConfig

config = OrchestratorConfig(
    raise_on_leak=True  # Raises DataLeakageError instead of redacting
)
```

### Custom Entropy Threshold

Lower threshold = more sensitive (more false positives):

```bash
# Default: 4.5
export RLM_ENTROPY_THRESHOLD=4.0  # More sensitive
```

## Monitoring

### Log Analysis

```python
import logging

# Enable RLM logging
logging.getLogger("rlm").setLevel(logging.INFO)

# Watch for these patterns:
# - "Security runtime 'runsc' detected" ✅
# - "Using standard 'runc'" ⚠️
# - "High entropy detected" 🔍
# - "Secret pattern matched" 🔍
```

### Metrics to Track

| Metric | Why |
|--------|-----|
| Execution time | Detect anomalies |
| Memory usage | Prevent abuse |
| Iteration count | Catch infinite loops |
| Egress filter triggers | Security incidents |

## Network Risks

If you must enable network:

!!! warning "High Risk"
    Enabling network allows:
    
    - Data exfiltration to external servers
    - Downloading malicious payloads
    - C2 (Command & Control) communication
    - Crypto mining pool connections

**Mitigations** (if network required):

1. Use network policies to whitelist specific domains
2. Monitor egress traffic
3. Rate limit requests
4. Use a proxy with logging

## Incident Response

### If You Detect a Leak

1. **Stop** the orchestrator immediately
2. **Review** execution logs
3. **Identify** what was leaked
4. **Rotate** any exposed credentials
5. **Analyze** how the leak occurred

### If Container Escapes

1. **Isolate** the host
2. **Capture** forensic data
3. **Review** gVisor logs (`runsc logs`)
4. **Report** to gVisor maintainers if it's a new escape

## Security Checklist

Before going live:

- [ ] gVisor installed and tested
- [ ] `docker run --runtime=runsc hello-world` works
- [ ] `RLM_ALLOW_UNSAFE_RUNTIME=0`
- [ ] `RLM_NETWORK_ENABLED=0`
- [ ] Resource limits set appropriately
- [ ] Logging enabled
- [ ] Monitoring in place
- [ ] Incident response plan documented
