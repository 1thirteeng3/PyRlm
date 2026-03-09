
import asyncio
import logging
import sys
import traceback
from pathlib import Path

# Add src to python path if needed (though running as -m is better, we'll facilitate script usage)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rlm.core.orchestrator import Orchestrator, OrchestratorConfig
from rlm.llm.base import BaseLLMClient, LLMResponse, Message, TokenUsage
from rlm.core.repl.docker import ExecutionResult

logging.basicConfig(level=logging.DEBUG)

class MockLLMClient(BaseLLMClient):
    def __init__(self):
        super().__init__(api_key="mock", model="mock-model")
    @property
    def provider_name(self) -> str: return "mock"
    def complete(self, messages, **kwargs): return self._generate_response()
    def stream(self, messages, **kwargs): yield self._generate_response().content
    async def acomplete(self, messages, **kwargs): return self._generate_response()
    async def astream(self, messages, **kwargs): yield self._generate_response().content
    def _generate_response(self):
        return LLMResponse(content="```python\nprint('hello')\n```", model="mock-model")

class LocalSandbox:
    async def execute_async(self, code: str, context_mount=None):
        return ExecutionResult(stdout="hello", stderr="", exit_code=0)

async def run():
    print("Starting debug run...")
    try:
        llm = MockLLMClient()
        sandbox = LocalSandbox()
        config = OrchestratorConfig(max_iterations=1)
        orchestrator = Orchestrator(llm_client=llm, sandbox=sandbox, config=config)
        print("Orchestrator initialized.")
        result = await orchestrator.arun("test")
        print(f"Result: {result}")
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
