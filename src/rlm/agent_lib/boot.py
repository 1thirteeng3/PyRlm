#!/usr/bin/env python3
"""
RLM Agent Boot Script - Entry point for code execution in sandbox.

This script is the clean entry point that runs inside the Docker container.
It sets up the environment and executes the user code.

Usage inside container:
    python3 -m rlm_agent_lib.boot --code-file /tmp/user_code.py
    python3 -m rlm_agent_lib.boot --code "print('hello')"
"""

import argparse
import sys
import traceback
from pathlib import Path
from typing import Optional

# Import agent utilities
from rlm.agent_lib.context import ContextHandle, ctx
from rlm.agent_lib.utils import emit_final, emit_progress


def setup_environment() -> dict:
    """
    Set up the execution environment with agent utilities.
    
    Returns:
        Dictionary of globals to use for exec()
    """
    env = {
        # Built-ins
        "__name__": "__main__",
        "__doc__": None,
        "__package__": None,
        
        # Agent utilities
        "ContextHandle": ContextHandle,
        "ctx": ctx,
        "emit_final": emit_final,
        "emit_progress": emit_progress,
        "FINAL": emit_final,  # Alias
        
        # Common imports (pre-loaded for convenience)
        "re": __import__("re"),
        "json": __import__("json"),
        "math": __import__("math"),
        "os": __import__("os"),
    }
    
    # Try to import optional data science libraries
    try:
        env["numpy"] = __import__("numpy")
        env["np"] = env["numpy"]
    except ImportError:
        pass
    
    try:
        env["pandas"] = __import__("pandas")
        env["pd"] = env["pandas"]
    except ImportError:
        pass
    
    return env


def execute_code(code: str, env: dict) -> None:
    """
    Execute the user code in the prepared environment.
    
    Args:
        code: Python code to execute
        env: Environment dictionary for exec()
    """
    try:
        # Compile for better error messages
        compiled = compile(code, "<agent_code>", "exec")
        exec(compiled, env)
    except Exception as e:
        # Print traceback for debugging
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


def main() -> None:
    """Main entry point for the boot script."""
    parser = argparse.ArgumentParser(description="RLM Agent Boot Script")
    parser.add_argument(
        "--code",
        type=str,
        help="Python code to execute directly",
    )
    parser.add_argument(
        "--code-file",
        type=str,
        help="Path to Python file to execute",
    )
    parser.add_argument(
        "--context",
        type=str,
        default="/mnt/context",
        help="Path to context file (default: /mnt/context)",
    )
    
    args = parser.parse_args()
    
    # Determine code source
    code: Optional[str] = None
    
    if args.code:
        code = args.code
    elif args.code_file:
        code_path = Path(args.code_file)
        if not code_path.exists():
            print(f"ERROR: Code file not found: {args.code_file}", file=sys.stderr)
            sys.exit(1)
        code = code_path.read_text(encoding="utf-8")
    else:
        # Read from stdin
        code = sys.stdin.read()
    
    if not code or not code.strip():
        print("ERROR: No code provided", file=sys.stderr)
        sys.exit(1)
    
    # Set up environment
    env = setup_environment()
    
    # Update context path if custom
    if args.context != "/mnt/context" and Path(args.context).exists():
        env["ctx"] = ContextHandle(args.context)
    
    # Execute
    execute_code(code, env)


if __name__ == "__main__":
    main()
