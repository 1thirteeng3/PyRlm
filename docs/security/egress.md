# Egress Filtering

Prevent data leaks from sandbox output.

## Overview

RLM's egress filter inspects all output from code execution and blocks potential secret leakage.

```mermaid
graph LR
    A[Code Output] --> B{Egress Filter}
    B -->|Clean| C[Return to LLM]
    B -->|Secret Detected| D[Redact/Block]
```

## Detection Methods

### 1. Shannon Entropy

High-entropy strings indicate secrets:

```
"Hello world"     → Entropy: 3.2  ✅ OK
"sk-a1b2c3d4..."  → Entropy: 5.1  🚫 BLOCKED
```

**How it works:**

- Calculate information entropy of string segments
- Threshold default: 4.5 bits
- Higher entropy → more random → likely a secret

### 2. Pattern Matching

Known secret formats are detected:

| Pattern | Example |
|---------|---------|
| AWS Access Key | `AKIAIOSFODNN7EXAMPLE` |
| AWS Secret Key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| Private Key | `-----BEGIN RSA PRIVATE KEY-----` |
| JWT Token | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |
| Bearer Token | `Bearer sk-...` |
| Generic API Key | `api_key=...`, `apikey: ...` |

### 3. Context Echo Prevention

If you provided a context file, the filter prevents echoing sensitive portions:

```python
# If context contains: database_password=secret123
# And output contains: "The password is secret123"
# → BLOCKED: Context echo detected
```

### 4. Binary Magic Bytes (v3.0)

Binary data is detected and blocked:

| Magic Bytes | File Type |
|-------------|-----------|
| `\x89PNG` | PNG Image |
| `PK\x03\x04` | ZIP Archive |
| `%PDF` | PDF Document |
| `\x7fELF` | Executable |
| `GIF89` | GIF Image |
| `MZ` | Windows EXE |

## Configuration

```bash
# Entropy threshold (lower = more sensitive)
export RLM_ENTROPY_THRESHOLD=4.5

# Context similarity threshold
export RLM_SIMILARITY_THRESHOLD=0.8

# Max output size (bytes)
export RLM_MAX_STDOUT_BYTES=4000
```

## Behavior Options

### Redact (Default)

Secrets are replaced with `[REDACTED]`:

```python
# Output: "API_KEY=sk-abc123xyz"
# Filtered: "API_KEY=[REDACTED: Secret Pattern]"
```

### Raise Exception

Fail instead of redacting:

```python
from rlm.core import OrchestratorConfig

config = OrchestratorConfig(raise_on_leak=True)
agent = Orchestrator(config=config)

try:
    result = agent.run("print(os.environ.get('API_KEY'))")
except DataLeakageError as e:
    print(f"Leak blocked: {e.leak_type}")
```

## Direct Filter Usage

```python
from rlm.security.egress import EgressFilter

# Create filter
filter = EgressFilter(context="my secret password here")

# Filter output
output = "The password is my secret password"
filtered = filter.filter(output, raise_on_leak=False)
# → "The password is [REDACTED: Context Echo]"
```

## Detection Functions

### Check for Secrets

```python
from rlm.security.egress import detect_secrets

text = "My AWS key is AKIAIOSFODNN7EXAMPLE"
findings = detect_secrets(text)

for finding in findings:
    print(f"Found: {finding.pattern_name} at position {finding.start}")
```

### Calculate Entropy

```python
from rlm.security.egress import calculate_shannon_entropy

entropy = calculate_shannon_entropy("sk-a1b2c3d4e5f6")
print(f"Entropy: {entropy:.2f}")  # ~5.0 - suspicious!
```

## Allowlist

Some high-entropy strings are safe (hashes, UUIDs):

```python
# These are NOT flagged:
# - Git commit hashes
# - MD5/SHA hashes
# - UUIDs
# - Base64 encoded safe content

entropy_allowlist = [
    r'^[a-f0-9]{32}$',  # MD5
    r'^[a-f0-9]{40}$',  # SHA1
    r'^[a-f0-9]{64}$',  # SHA256
]
```

## False Positives

If you're getting false positives:

1. **Raise the threshold**:
   ```bash
   export RLM_ENTROPY_THRESHOLD=5.0
   ```

2. **Review what's being blocked**:
   ```python
   from rlm.security.egress import calculate_shannon_entropy
   
   text = "your_output_here"
   print(f"Entropy: {calculate_shannon_entropy(text)}")
   ```

3. **Consider if it's actually sensitive** - high entropy might be legitimate data.
