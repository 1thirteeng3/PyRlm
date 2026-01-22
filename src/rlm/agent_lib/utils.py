"""
Utility functions available inside the sandbox.

These functions provide additional capabilities to the agent
running inside the Docker container.
"""

import json
from typing import Any, Optional


def llm_query(prompt: str, context_chunk: str = "") -> str:
    """
    Query the LLM for semantic processing of a text chunk.
    
    This is a placeholder that will be replaced by the actual
    implementation when running inside the orchestrator's sandbox.
    
    Args:
        prompt: The question or instruction for the LLM
        context_chunk: Optional text context to analyze
        
    Returns:
        The LLM's response
    """
    # This function is injected/replaced at runtime by the orchestrator
    raise NotImplementedError(
        "llm_query is not available in standalone mode. "
        "Use the Orchestrator to execute code with LLM access."
    )


def emit_final(answer: Any) -> None:
    """
    Emit the final answer and signal completion.
    
    Args:
        answer: The final answer (will be converted to string)
    """
    if isinstance(answer, (dict, list)):
        answer = json.dumps(answer, ensure_ascii=False, indent=2)
    print(f"FINAL({answer})")


def emit_progress(message: str, progress: Optional[float] = None) -> None:
    """
    Emit a progress update.
    
    Args:
        message: Progress message
        progress: Optional progress percentage (0.0-1.0)
    """
    if progress is not None:
        print(f"PROGRESS({progress:.1%}): {message}")
    else:
        print(f"PROGRESS: {message}")
