"""
Main Orchestrator for RLM.

This module provides the core agent loop that coordinates between
the LLM, sandbox execution, and egress filtering.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from rlm.config.settings import settings
from rlm.core.exceptions import BudgetExceededError, RLMError, SandboxError
from rlm.core.repl.docker import DockerSandbox, ExecutionResult
from rlm.llm.base import BaseLLMClient, LLMResponse, Message
from rlm.llm.factory import create_llm_client
from rlm.prompt_templates.system import get_system_prompt
from rlm.security.egress import EgressFilter
from rlm.utils.cost import BudgetManager

logger = logging.getLogger(__name__)


# Pattern to extract code blocks from LLM responses
CODE_BLOCK_PATTERN = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)

# Pattern to detect final answer
FINAL_ANSWER_PATTERN = re.compile(r"FINAL\s*\((.*?)\)", re.DOTALL)


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator."""

    max_iterations: int = field(default_factory=lambda: settings.max_recursion_depth)
    context_path: Optional[Path] = None
    system_prompt_mode: str = "full"
    custom_instructions: Optional[str] = None
    raise_on_leak: bool = False


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
    Main orchestrator for RLM code execution.

    Coordinates the agent loop:
    1. Send user query to LLM with system prompt
    2. Parse LLM response for code blocks
    3. Execute code in sandbox
    4. Filter output and send back to LLM
    5. Repeat until FINAL() is emitted or max iterations reached

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
            self._sandbox = DockerSandbox()
        return self._sandbox

    def _get_system_prompt(self) -> str:
        """Build the system prompt."""
        context_available = self.config.context_path is not None
        return get_system_prompt(
            mode=self.config.system_prompt_mode,
            context_available=context_available,
            custom_instructions=self.config.custom_instructions,
        )

    def _extract_code_blocks(self, text: str) -> list[str]:
        """Extract Python code blocks from LLM response."""
        blocks = CODE_BLOCK_PATTERN.findall(text)
        return [block.strip() for block in blocks if block.strip()]

    def _extract_final_answer(self, text: str) -> Optional[str]:
        """Extract final answer from LLM response or code output."""
        match = FINAL_ANSWER_PATTERN.search(text)
        if match:
            return match.group(1).strip()
        return None

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

    def run(
        self,
        query: str,
        context_path: Optional[str | Path] = None,
    ) -> OrchestratorResult:
        """
        Run the orchestration loop for a user query.

        Args:
            query: User's question or task
            context_path: Optional path to context file

        Returns:
            OrchestratorResult with the final answer and execution details
        """
        # Reset state
        self.history = []
        self.steps = []

        # Setup context if provided
        if context_path:
            self.config.context_path = Path(context_path)
            # Create egress filter with context
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
                assistant_message = response.content

                # Check for final answer in LLM response
                final_answer = self._extract_final_answer(assistant_message)
                if final_answer:
                    self.steps.append(ExecutionStep(
                        iteration=iteration,
                        action="final_answer",
                        input_data=assistant_message,
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
                self.history.append(Message(role="assistant", content=assistant_message))

                # Extract and execute code blocks
                code_blocks = self._extract_code_blocks(assistant_message)

                if not code_blocks:
                    # No code to execute - LLM might be answering directly
                    # Check if this looks like a final answer
                    if iteration > 0:  # After first iteration, treat as final
                        return OrchestratorResult(
                            final_answer=assistant_message,
                            success=True,
                            iterations=iteration + 1,
                            steps=self.steps,
                            budget_summary=self.budget.summary(),
                        )
                    continue

                # Execute each code block
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
                    final_answer = self._extract_final_answer(result.stdout)
                    if final_answer:
                        self.steps.append(ExecutionStep(
                            iteration=iteration,
                            action="final_answer",
                            input_data=result.stdout,
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

                # Add observation to history
                observation = "\n---\n".join(combined_output)
                self.history.append(Message(
                    role="user",
                    content=f"Observation:\n{observation}",
                ))

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

    def chat(self, message: str) -> str:
        """
        Simple chat interface for one-off questions.

        This is a simplified interface that runs a single iteration
        and returns the response directly.

        Args:
            message: User message

        Returns:
            Assistant response
        """
        result = self.run(message)
        return result.final_answer or result.steps[-1].output_data if result.steps else ""
