# LLM Clients API

## Base Client

::: rlm.llm.base.BaseLLMClient
    options:
      show_source: true
      members:
        - complete
        - stream
        - validate_api_key
        - provider_name

::: rlm.llm.base.Message

::: rlm.llm.base.LLMResponse

::: rlm.llm.base.TokenUsage

## OpenAI Client

::: rlm.llm.openai_client.OpenAIClient
    options:
      show_source: true

## Anthropic Client

::: rlm.llm.anthropic_client.AnthropicClient
    options:
      show_source: true

## Google Client

::: rlm.llm.google_client.GoogleClient
    options:
      show_source: true

## Factory Function

::: rlm.llm.factory.create_llm_client
