"""
Main Orchestrator for RLM v3.0 (The Perfection Update).

v3.0 Changes:
- DRY: Single source of truth via _execute_cycle()
- run() is now a pure sync wrapper
- CPU offloading for egress filtering
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Optional

from rlm.config.settings import settings
from rlm.core.exceptions import BudgetExceededError, RLMError, SandboxError
from rlm.core.parsing import extract_python_code, extract_final_answer
from rlm.core.repl.docker import DockerSandbox, ExecutionResult
from rlm.llm.base import BaseLLMClient, LLMResponse, Message
from rlm.llm.factory import create_llm_client
from rlm.prompt_templates.system import get_system_prompt
from rlm.security.egress import EgressFilter
from rlm.utils.cost import BudgetManager

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator."""

    max_iterations: int = field(default_factory=lambda: settings.max_recursion_depth)
    context_path: Optional[Path] = None
    system_prompt_mode: str = "full"
    custom_instructions: Optional[str] = None
    raise_on_leak: bool = False
    allow_unsafe_runtime: bool = False


@dataclass
class ExecutionStep:
    """Record of a single execution step."""

    iteration: int
    action: str  # "llm_call", "code_execution", "final_answer"
    input_data: str
    output_data: str
    success: bool
    error: Optional[str] = None


@dataclass
class OrchestratorResult:
    """Result of an orchestration run."""

    final_answer: Optional[str]
    success: bool
    iterations: int
    steps: list[ExecutionStep]
    budget_summary: dict
    error: Optional[str] = None


class Orchestrator:
    """
    Main orchestrator for RLM code execution (v3.0).

    v3.0 Architecture:
    - _execute_cycle() is the Single Source of Truth
    - arun() is the public async interface
    - run() is a pure sync wrapper (no duplicated logic)
    - CPU-bound egress filtering runs in ThreadPoolExecutor

    Example:
        >>> orchestrator = Orchestrator()
        >>> result = orchestrator.run("What is 2+2?")  # Sync
        >>> result = await orchestrator.arun("What is 2+2?")  # Async
    """

    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        sandbox: Optional[DockerSandbox] = None,
        config: Optional[OrchestratorConfig] = None,
    ) -> None:
        """Initialize the orchestrator."""
        self.config = config or OrchestratorConfig()
        self._llm_client = llm_client
        self._sandbox = sandbox
        self.budget = BudgetManager()
        self.egress_filter: Optional[EgressFilter] = None
        self.history: list[Message] = []
        self.steps: list[ExecutionStep] = []

    @property
    def llm(self) -> BaseLLMClient:
        """Lazy-load LLM client."""
        if self._llm_client is None:
            self._llm_client = create_llm_client()
        return self._llm_client

    @property
    def sandbox(self) -> DockerSandbox:
        """Lazy-load Docker sandbox."""
        if self._sandbox is None:
            from rlm.core.repl.docker import SandboxConfig
            sandbox_config = SandboxConfig(
                allow_unsafe_runtime=self.config.allow_unsafe_runtime,
            )
            self._sandbox = DockerSandbox(config=sandbox_config)
        return self._sandbox

    def _get_system_prompt(self) -> str:
        """Build the system prompt."""
        context_available = self.config.context_path is not None
        return get_system_prompt(
            mode=self.config.system_prompt_mode,
            context_available=context_available,
            custom_instructions=self.config.custom_instructions,
        )

    # ==================== Core Async Methods ====================

    async def _acall_llm(self, iteration: int) -> LLMResponse:
        """Call the LLM asynchronously."""
        system_prompt = self._get_system_prompt()

        response = await self.llm.acomplete(
            messages=self.history,
            system_prompt=system_prompt,
        )

        self.budget.record_usage(
            model=response.model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )

        self.steps.append(ExecutionStep(
            iteration=iteration,
            action="llm_call",
            input_data=self.history[-1].content if self.history else "",
            output_data=response.content,
            success=True,
        ))

        return response

    async def _aexecute_code(self, code: str, iteration: int) -> ExecutionResult:
        """
        Execute code asynchronously with CPU offloading for egress filter.
        
        v3.0: Egress filtering runs in ThreadPoolExecutor to avoid blocking.
        """
        context_mount = str(self.config.context_path) if self.config.context_path else None

        try:
            result = await self.sandbox.execute_async(code, context_mount=context_mount)

            # v3.0: CPU OFFLOAD - Move heavy egress filtering to thread pool
            if self.egress_filter:
                loop = asyncio.get_running_loop()
                filter_func = partial(
                    self.egress_filter.filter,
                    result.stdout,
                    raise_on_leak=self.config.raise_on_leak,
                )
                result.stdout = await loop.run_in_executor(None, filter_func)

            self.steps.append(ExecutionStep(
                iteration=iteration,
                action="code_execution",
                input_data=code,
                output_data=result.stdout,
                success=result.success,
                error=result.stderr if not result.success else None,
            ))

            return result

        except SandboxError as e:
            self.steps.append(ExecutionStep(
                iteration=iteration,
                action="code_execution",
                input_data=code,
                output_data="",
                success=False,
                error=str(e),
            ))
            raise

    # ==================== Single Source of Truth ====================

    async def _execute_cycle(
        self,
        query: str,
        context_path: Optional[Path],
    ) -> OrchestratorResult:
        """
        Core logic (Single Source of Truth).
        
        v3.0: All orchestration logic lives here. Both run() and arun()
        delegate to this method, eliminating code duplication.
        
        Contains the complete loop: LLM -> Parse -> Execute -> Filter.
        """
        # Reset state
        self.history = []
        self.steps = []

        # Setup context
        if context_path:
            self.config.context_path = context_path
            # Read context sample in thread to avoid blocking
            loop = asyncio.get_running_loop()
            context_sample = await loop.run_in_executor(
                None,
                lambda: Path(context_path).read_text(encoding="utf-8", errors="replace")[:5000]
            )
            self.egress_filter = EgressFilter(context=context_sample)
        else:
            self.egress_filter = EgressFilter()

        # Add initial user message
        self.history.append(Message(role="user", content=query))

        try:
            for iteration in range(self.config.max_iterations):
                logger.info(f"Iteration {iteration + 1}/{self.config.max_iterations}")

                # 1. Call LLM
                response = await self._acall_llm(iteration)

                # 2. Check for final answer in LLM response
                final_answer = extract_final_answer(response.content)
                if final_answer:
                    self.steps.append(ExecutionStep(
                        iteration=iteration,
                        action="final_answer",
                        input_data=response.content,
                        output_data=final_answer,
                        success=True,
                    ))
                    return OrchestratorResult(
                        final_answer=final_answer,
                        success=True,
                        iterations=iteration + 1,
                        steps=self.steps,
                        budget_summary=self.budget.summary(),
                    )

                # Add assistant response to history
                self.history.append(Message(role="assistant", content=response.content))

                # 3. Parse code blocks using strict mistletoe parser
                code_blocks = extract_python_code(response.content)

                if not code_blocks:
                    # No code - might be final answer or needs more info
                    if iteration > 0:
                        return OrchestratorResult(
                            final_answer=response.content,
                            success=True,
                            iterations=iteration + 1,
                            steps=self.steps,
                            budget_summary=self.budget.summary(),
                        )
                    continue

                # 4. Execute code blocks
                combined_output = []
                for code in code_blocks:
                    result = await self._aexecute_code(code, iteration)

                    if result.oom_killed:
                        combined_output.append("Error: Memory Limit Exceeded (OOMKilled)")
                    elif result.timed_out:
                        combined_output.append("Error: Execution Timeout")
                    elif not result.success:
                        combined_output.append(f"Error (exit {result.exit_code}):\n{result.stderr}")
                    else:
                        combined_output.append(result.stdout)

                    # Check for final answer in code output
                    final = extract_final_answer(result.stdout)
                    if final:
                        self.steps.append(ExecutionStep(
                            iteration=iteration,
                            action="final_answer",
                            input_data=result.stdout,
                            output_data=final,
                            success=True,
                        ))
                        return OrchestratorResult(
                            final_answer=final,
                            success=True,
                            iterations=iteration + 1,
                            steps=self.steps,
                            budget_summary=self.budget.summary(),
                        )

                # 5. Add observation to history
                observation = "\n---\n".join(combined_output)
                self.history.append(Message(role="user", content=f"Observation:\n{observation}"))

            # Max iterations reached
            return OrchestratorResult(
                final_answer=None,
                success=False,
                iterations=self.config.max_iterations,
                steps=self.steps,
                budget_summary=self.budget.summary(),
                error="Max iterations reached without final answer",
            )

        except BudgetExceededError as e:
            return OrchestratorResult(
                final_answer=None,
                success=False,
                iterations=len([s for s in self.steps if s.action == "llm_call"]),
                steps=self.steps,
                budget_summary=self.budget.summary(),
                error=str(e),
            )

        except RLMError as e:
            return OrchestratorResult(
                final_answer=None,
                success=False,
                iterations=len([s for s in self.steps if s.action == "llm_call"]),
                steps=self.steps,
                budget_summary=self.budget.summary(),
                error=str(e),
            )

    # ==================== Public Interfaces ====================

    async def arun(
        self,
        query: str,
        context_path: Optional[str | Path] = None,
    ) -> OrchestratorResult:
        """
        Run the orchestration loop (asynchronous).

        v3.0: Delegates to _execute_cycle() (Single Source of Truth).

        Args:
            query: User's question or task
            context_path: Optional path to context file

        Returns:
            OrchestratorResult with the final answer
        """
        path = Path(context_path) if context_path else None
        return await self._execute_cycle(query, path)

    def run(
        self,
        query: str,
        context_path: Optional[str | Path] = None,
    ) -> OrchestratorResult:
        """
        Run the orchestration loop (synchronous wrapper).

        v3.0: Pure wrapper with NO duplicated logic.
        Creates a disposable event loop or uses existing one safely.

        Args:
            query: User's question or task
            context_path: Optional path to context file

        Returns:
            OrchestratorResult with the final answer
        """
        try:
            # Standard case: no event loop running
            return asyncio.run(self.arun(query, context_path))
        except RuntimeError:
            # Fallback: event loop already running (e.g., Jupyter, some web frameworks)
            # This requires the existing loop to be cooperative
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Cannot use run_until_complete on running loop
                # User should use arun() directly in async contexts
                raise RuntimeError(
                    "Event loop is already running. Use 'await orchestrator.arun()' "
                    "in async contexts, or use nest_asyncio if needed."
                )
            return loop.run_until_complete(self.arun(query, context_path))

    def chat(self, message: str) -> str:
        """Simple chat interface for one-off questions."""
        result = self.run(message)
        return result.final_answer or (result.steps[-1].output_data if result.steps else "")
