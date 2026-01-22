"""
Main Orchestrator for RLM v2.1.

Coordinates the agent loop with:
- Robust markdown parsing (mistletoe)
- Async support for non-blocking execution
- Clean boot sandbox integration
- Budget tracking and egress filtering
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
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
    # v2.1: Allow unsafe runtime for development
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
    Main orchestrator for RLM code execution (v2.1).

    v2.1 Changes:
    - Uses robust markdown parsing (mistletoe)
    - Supports async execution via arun()
    - Integrates with clean boot sandbox
    - Fail-closed security by default

    Workflow:
    1. Send user query to LLM with system prompt
    2. Parse LLM response for code blocks (robust parsing)
    3. Execute code in sandbox (clean boot)
    4. Filter output through egress controls
    5. Repeat until FINAL() or max iterations

    Example:
        >>> orchestrator = Orchestrator()
        >>> result = orchestrator.run("What is 2+2?")
        >>> print(result.final_answer)
        4
    """

    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        sandbox: Optional[DockerSandbox] = None,
        config: Optional[OrchestratorConfig] = None,
    ) -> None:
        """
        Initialize the orchestrator.

        Args:
            llm_client: LLM client (created from settings if not provided)
            sandbox: Docker sandbox (created if not provided)
            config: Orchestrator configuration
        """
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

    def _call_llm(self, iteration: int) -> LLMResponse:
        """Call the LLM and track the cost."""
        system_prompt = self._get_system_prompt()

        response = self.llm.complete(
            messages=self.history,
            system_prompt=system_prompt,
        )

        # Track cost
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

    def _execute_code(self, code: str, iteration: int) -> ExecutionResult:
        """Execute code in the sandbox."""
        context_mount = str(self.config.context_path) if self.config.context_path else None

        try:
            result = self.sandbox.execute(code, context_mount=context_mount)

            # Apply egress filter
            if self.egress_filter:
                result.stdout = self.egress_filter.filter(
                    result.stdout,
                    raise_on_leak=self.config.raise_on_leak,
                )

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

    async def _aexecute_code(self, code: str, iteration: int) -> ExecutionResult:
        """Execute code asynchronously."""
        context_mount = str(self.config.context_path) if self.config.context_path else None

        try:
            result = await self.sandbox.execute_async(code, context_mount=context_mount)

            if self.egress_filter:
                result.stdout = self.egress_filter.filter(
                    result.stdout,
                    raise_on_leak=self.config.raise_on_leak,
                )

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

    def _process_iteration(
        self,
        iteration: int,
        assistant_message: str,
    ) -> tuple[Optional[str], bool]:
        """
        Process a single iteration.
        
        Returns:
            Tuple of (final_answer, should_continue)
        """
        # Check for final answer in LLM response
        final_answer = extract_final_answer(assistant_message)
        if final_answer:
            self.steps.append(ExecutionStep(
                iteration=iteration,
                action="final_answer",
                input_data=assistant_message,
                output_data=final_answer,
                success=True,
            ))
            return final_answer, False

        # Add assistant response to history
        self.history.append(Message(role="assistant", content=assistant_message))

        # v2.1: Use robust parser instead of regex
        code_blocks = extract_python_code(assistant_message)

        if not code_blocks:
            # No code - might be final answer
            if iteration > 0:
                return assistant_message, False
            return None, True

        # Execute code blocks
        combined_output = []
        for code in code_blocks:
            result = self._execute_code(code, iteration)

            if result.oom_killed:
                combined_output.append("Error: Memory Limit Exceeded (OOMKilled)")
            elif result.timed_out:
                combined_output.append("Error: Execution Timeout")
            elif not result.success:
                combined_output.append(f"Error (exit {result.exit_code}):\n{result.stderr}")
            else:
                combined_output.append(result.stdout)

            # Check for final answer in output
            final = extract_final_answer(result.stdout)
            if final:
                self.steps.append(ExecutionStep(
                    iteration=iteration,
                    action="final_answer",
                    input_data=result.stdout,
                    output_data=final,
                    success=True,
                ))
                return final, False

        # Add observation
        observation = "\n---\n".join(combined_output)
        self.history.append(Message(role="user", content=f"Observation:\n{observation}"))

        return None, True

    def run(
        self,
        query: str,
        context_path: Optional[str | Path] = None,
    ) -> OrchestratorResult:
        """
        Run the orchestration loop (synchronous).

        Args:
            query: User's question or task
            context_path: Optional path to context file

        Returns:
            OrchestratorResult with the final answer and execution details
        """
        # Reset state
        self.history = []
        self.steps = []

        # Setup context
        if context_path:
            self.config.context_path = Path(context_path)
            context_sample = Path(context_path).read_text(encoding="utf-8", errors="replace")[:5000]
            self.egress_filter = EgressFilter(context=context_sample)
        else:
            self.egress_filter = EgressFilter()

        # Add initial user message
        self.history.append(Message(role="user", content=query))

        try:
            for iteration in range(self.config.max_iterations):
                logger.info(f"Iteration {iteration + 1}/{self.config.max_iterations}")

                # Call LLM
                response = self._call_llm(iteration)

                # Process response
                final_answer, should_continue = self._process_iteration(
                    iteration, response.content
                )

                if not should_continue:
                    return OrchestratorResult(
                        final_answer=final_answer,
                        success=True,
                        iterations=iteration + 1,
                        steps=self.steps,
                        budget_summary=self.budget.summary(),
                    )

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

    async def arun(
        self,
        query: str,
        context_path: Optional[str | Path] = None,
    ) -> OrchestratorResult:
        """
        Run the orchestration loop (asynchronous).

        v2.1: True async for non-blocking I/O in async frameworks.

        Args:
            query: User's question or task
            context_path: Optional path to context file

        Returns:
            OrchestratorResult with the final answer
        """
        # Reset state
        self.history = []
        self.steps = []

        # Setup context
        if context_path:
            self.config.context_path = Path(context_path)
            context_sample = await asyncio.to_thread(
                lambda: Path(context_path).read_text(encoding="utf-8", errors="replace")[:5000]
            )
            self.egress_filter = EgressFilter(context=context_sample)
        else:
            self.egress_filter = EgressFilter()

        self.history.append(Message(role="user", content=query))

        try:
            for iteration in range(self.config.max_iterations):
                logger.info(f"Async iteration {iteration + 1}/{self.config.max_iterations}")

                response = await self._acall_llm(iteration)

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

                self.history.append(Message(role="assistant", content=response.content))
                code_blocks = extract_python_code(response.content)

                if not code_blocks:
                    if iteration > 0:
                        return OrchestratorResult(
                            final_answer=response.content,
                            success=True,
                            iterations=iteration + 1,
                            steps=self.steps,
                            budget_summary=self.budget.summary(),
                        )
                    continue

                # Execute async
                combined_output = []
                for code in code_blocks:
                    result = await self._aexecute_code(code, iteration)

                    if result.oom_killed:
                        combined_output.append("Error: OOMKilled")
                    elif result.timed_out:
                        combined_output.append("Error: Timeout")
                    elif not result.success:
                        combined_output.append(f"Error:\n{result.stderr}")
                    else:
                        combined_output.append(result.stdout)

                    final = extract_final_answer(result.stdout)
                    if final:
                        return OrchestratorResult(
                            final_answer=final,
                            success=True,
                            iterations=iteration + 1,
                            steps=self.steps,
                            budget_summary=self.budget.summary(),
                        )

                observation = "\n---\n".join(combined_output)
                self.history.append(Message(role="user", content=f"Observation:\n{observation}"))

            return OrchestratorResult(
                final_answer=None,
                success=False,
                iterations=self.config.max_iterations,
                steps=self.steps,
                budget_summary=self.budget.summary(),
                error="Max iterations reached",
            )

        except (BudgetExceededError, RLMError) as e:
            return OrchestratorResult(
                final_answer=None,
                success=False,
                iterations=len([s for s in self.steps if s.action == "llm_call"]),
                steps=self.steps,
                budget_summary=self.budget.summary(),
                error=str(e),
            )

    def chat(self, message: str) -> str:
        """Simple chat interface for one-off questions."""
        result = self.run(message)
        return result.final_answer or result.steps[-1].output_data if result.steps else ""
