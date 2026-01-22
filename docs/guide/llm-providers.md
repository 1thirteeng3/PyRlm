# LLM Providers

RLM supports multiple LLM providers with a unified interface.

## Supported Providers

| Provider | Models | Streaming |
|----------|--------|-----------|
| OpenAI | GPT-4, GPT-4o, GPT-4o-mini | ✅ |
| Anthropic | Claude 3 Opus, Sonnet, Haiku | ✅ |
| Google | Gemini 1.5 Pro | ✅ |

## Configuration

### OpenAI

```bash
RLM_API_PROVIDER=openai
RLM_API_KEY=sk-...
RLM_MODEL_NAME=gpt-4o
```

### Anthropic

```bash
RLM_API_PROVIDER=anthropic
RLM_API_KEY=sk-ant-api03-...
RLM_MODEL_NAME=claude-3-sonnet-20240229
```

### Google

```bash
RLM_API_PROVIDER=google
RLM_API_KEY=AIza...
RLM_MODEL_NAME=gemini-1.5-pro
```

## Programmatic Usage

### Using the Factory

```python
from rlm.llm import create_llm_client

client = create_llm_client(
    provider="openai",
    api_key="sk-...",
    model="gpt-4o",
    temperature=0.0,
)
```

### Direct Client Usage

```python
from rlm.llm.openai_client import OpenAIClient
from rlm.llm.base import Message

client = OpenAIClient(
    api_key="sk-...",
    model="gpt-4o",
)

response = client.complete([
    Message(role="user", content="What is 2+2?")
])

print(response.content)  # "4"
print(response.usage.total_tokens)  # Token count
```

### Streaming

```python
for chunk in client.stream([
    Message(role="user", content="Write a haiku")
]):
    print(chunk, end="", flush=True)
```

## Custom System Prompts

```python
response = client.complete(
    messages=[Message(role="user", content="Hello")],
    system_prompt="You are a helpful assistant.",
)
```

## Response Object

```python
@dataclass
class LLMResponse:
    content: str              # Generated text
    model: str                # Model used
    usage: TokenUsage         # Token counts
    finish_reason: str        # Why generation stopped
    
@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
```

## Error Handling

```python
from rlm.core.exceptions import LLMError

try:
    response = client.complete([...])
except LLMError as e:
    print(f"Provider: {e.provider}")
    print(f"Error: {e.message}")
```
