# Egress Filtering

Egress filtering prevents sensitive data from leaking through code execution output.

## How It Works

The `EgressFilter` applies multiple detection layers:

1. **Entropy Detection** - High-entropy strings suggest secrets
2. **Pattern Matching** - Known secret formats (API keys, JWTs)
3. **Context Echo** - Prevents printing raw context back
4. **Size Limiting** - Truncates excessive output

## Detection Methods

### Shannon Entropy

Secrets have high entropy (randomness). Normal text has lower entropy.

| Content Type | Typical Entropy |
|--------------|-----------------|
| Repetitive text | 0-2 |
| Natural language | 2-4 |
| Code | 4-4.5 |
| Secrets/keys | 4.5-6+ |

```python
from rlm.security.egress import calculate_shannon_entropy

# Normal text
entropy = calculate_shannon_entropy("Hello, how are you?")
print(f"Text entropy: {entropy:.2f}")  # ~3.5

# API key
entropy = calculate_shannon_entropy("sk-a1b2c3d4e5f6g7h8i9j0")
print(f"Key entropy: {entropy:.2f}")  # ~4.5+
```

### Pattern Detection

Known secret patterns are detected:

- AWS Access Keys (`AKIA...`)
- API Keys (`api_key=...`)
- Private Keys (`-----BEGIN...`)
- JWT Tokens (`eyJ...`)
- Bearer Tokens

```python
from rlm.security.egress import detect_secrets

text = "My key is sk-abc123def456ghi789"
secrets = detect_secrets(text)
print(secrets)  # [('api_key', 'sk-abc123def...')]
```

### Context Echo Prevention

Prevents the LLM from printing the raw context:

```python
from rlm.security.egress import EgressFilter

context = "Sensitive company data here..."
filter = EgressFilter(context=context)

# Try to echo the context
output = "Sensitive company data here..."
is_echo, similarity = filter.check_context_echo(output)
print(f"Echo detected: {is_echo}")  # True
```

## Using EgressFilter

### Basic Usage

```python
from rlm.security.egress import sanitize_output

raw_output = "Result: AKIAIOSFODNN7EXAMPLE"
safe_output = sanitize_output(raw_output)
print(safe_output)  # Result: [REDACTED: aws_access_key]
```

### With Context Protection

```python
from rlm.security.egress import EgressFilter

filter = EgressFilter(
    context="My secret document...",
    entropy_threshold=4.5,
    similarity_threshold=0.8,
)

output = filter.filter(raw_output)
```

### Raise on Leak

```python
from rlm.security.egress import sanitize_output
from rlm.core.exceptions import DataLeakageError

try:
    sanitize_output(
        "-----BEGIN RSA PRIVATE KEY-----",
        raise_on_leak=True
    )
except DataLeakageError as e:
    print(f"Leak prevented: {e}")
```

## Configuration

Adjust thresholds via environment variables:

```bash
RLM_ENTROPY_THRESHOLD=4.5      # Higher = less sensitive
RLM_SIMILARITY_THRESHOLD=0.8   # Higher = exact matches only
RLM_MIN_ENTROPY_LENGTH=256     # Minimum string length to check
RLM_MAX_STDOUT_BYTES=4000      # Truncation limit
```
