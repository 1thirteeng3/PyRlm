"""
Robust Markdown Code Block Parser.

v3.0: Strict mistletoe-only parsing.
- No regex fallback (fail-fast design)
- Direct AST parsing for reliability
- Binary files detected upstream in ContextHandle
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

# v3.0: Direct import - fail-fast if not installed
import mistletoe
from mistletoe.block_token import CodeFence


@dataclass
class CodeBlock:
    """Represents an extracted code block."""
    code: str
    language: str
    start_line: int
    end_line: int


def extract_code_blocks(text: str) -> List[CodeBlock]:
    """
    Extract all code blocks from markdown using mistletoe AST.
    
    v3.0: Uses pure AST parsing via mistletoe.
    No regex fallback - deterministic behavior guaranteed.
    
    Args:
        text: Markdown text containing code blocks
        
    Returns:
        List of CodeBlock objects with code, language, and positions
    """
    blocks: List[CodeBlock] = []
    
    with mistletoe.Document(text) as doc:
        _extract_from_tokens(doc.children, blocks)
    
    return blocks


def _extract_from_tokens(tokens: list, blocks: List[CodeBlock]) -> None:
    """Recursively extract code blocks from token tree."""
    for token in tokens:
        if isinstance(token, CodeFence):
            code = ""
            if token.children:
                # Extract raw content from children
                code = token.children[0].content if hasattr(token.children[0], 'content') else ""
            
            blocks.append(CodeBlock(
                code=code,
                language=token.language or "",
                start_line=getattr(token, 'line_number', 0),
                end_line=getattr(token, 'line_number', 0),
            ))
        
        # Recurse into nested tokens
        if hasattr(token, 'children') and token.children:
            _extract_from_tokens(token.children, blocks)


def extract_python_code(text: str) -> List[str]:
    """
    Extract Python code blocks from markdown text.
    
    Filters for Python language and returns just the code strings.
    
    Args:
        text: Markdown text containing code blocks
        
    Returns:
        List of Python code strings
    """
    blocks = extract_code_blocks(text)
    
    python_codes: List[str] = []
    for block in blocks:
        # Accept python, py, python3, or unspecified language
        if block.language.lower() in ('python', 'py', 'python3', ''):
            code = block.code.strip()
            if code:
                python_codes.append(code)
    
    return python_codes


def extract_final_answer(text: str) -> Optional[str]:
    """
    Extract a FINAL() answer from text.
    
    Supports multiple formats:
    - FINAL(answer)
    - FINAL: answer
    - Final Answer: answer
    
    Args:
        text: Text to search for final answer
        
    Returns:
        The extracted answer or None
    """
    import re
    
    patterns = [
        r'FINAL\s*\(\s*(.*?)\s*\)',  # FINAL(answer)
        r'FINAL\s*:\s*(.+?)(?:\n|$)',  # FINAL: answer
        r'Final\s+Answer\s*:\s*(.+?)(?:\n|$)',  # Final Answer: answer
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
    
    return None


def validate_python_syntax(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Python code syntax without executing.
    
    Args:
        code: Python code to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        compile(code, '<string>', 'exec')
        return True, None
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"
