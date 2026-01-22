# Configuration

RLM is configured via environment variables with the `RLM_` prefix or a `.env` file.

## Configuration File

Create a `.env` file in your project root:

```bash
# API Configuration
RLM_API_PROVIDER=openai
RLM_API_KEY=sk-your-api-key
RLM_MODEL_NAME=gpt-4o

# Execution
RLM_EXECUTION_MODE=docker
RLM_DOCKER_RUNTIME=auto

# Safety
RLM_COST_LIMIT_USD=5.0
RLM_MAX_RECURSION_DEPTH=5
```

## All Configuration Options

### API Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `RLM_API_PROVIDER` | string | `openai` | LLM provider: `openai`, `anthropic`, `google` |
| `RLM_API_KEY` | string | - | API key for the provider |
| `RLM_MODEL_NAME` | string | `gpt-4o` | Model name to use |

### Execution Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `RLM_EXECUTION_MODE` | string | `docker` | `docker` or `local` (dev only) |
| `RLM_DOCKER_RUNTIME` | string | `auto` | `auto`, `runsc`, or `runc` |
| `RLM_DOCKER_IMAGE` | string | `python:3.11-slim` | Docker image for sandbox |
| `RLM_EXECUTION_TIMEOUT` | int | `30` | Timeout in seconds (5-300) |

### Safety Limits

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `RLM_COST_LIMIT_USD` | float | `5.0` | Max spending per session |
| `RLM_MAX_RECURSION_DEPTH` | int | `5` | Max code execution iterations |
| `RLM_MAX_STDOUT_BYTES` | int | `4000` | Max output bytes captured |

### Security Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `RLM_MEMORY_LIMIT` | string | `512m` | Container memory limit |
| `RLM_CPU_LIMIT` | float | `1.0` | CPU cores limit (0.1-4.0) |
| `RLM_PIDS_LIMIT` | int | `50` | Max processes (10-200) |
| `RLM_NETWORK_ENABLED` | bool | `false` | Enable network (DANGEROUS) |

### Egress Filtering

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `RLM_ENTROPY_THRESHOLD` | float | `4.5` | Secret detection threshold (3.0-6.0) |
| `RLM_MIN_ENTROPY_LENGTH` | int | `256` | Min length for entropy check |
| `RLM_SIMILARITY_THRESHOLD` | float | `0.8` | Context echo threshold (0.5-1.0) |

## Programmatic Configuration

Override settings in code:

```python
from rlm.config import RLMSettings

# Create custom settings
custom_settings = RLMSettings(
    api_provider="anthropic",
    api_key="sk-ant-...",
    model_name="claude-3-sonnet-20240229",
    cost_limit_usd=10.0,
)
```

## Provider-Specific Models

### OpenAI

```bash
RLM_API_PROVIDER=openai
RLM_MODEL_NAME=gpt-4o          # Recommended
# RLM_MODEL_NAME=gpt-4-turbo
# RLM_MODEL_NAME=gpt-4o-mini
```

### Anthropic

```bash
RLM_API_PROVIDER=anthropic
RLM_MODEL_NAME=claude-3-sonnet-20240229   # Recommended
# RLM_MODEL_NAME=claude-3-opus-20240229
```

### Google

```bash
RLM_API_PROVIDER=google
RLM_MODEL_NAME=gemini-1.5-pro   # Recommended
```
