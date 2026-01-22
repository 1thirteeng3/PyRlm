"""
Robust Markdown Code Block Parser.

v2.1: Uses state machine instead of regex for reliable code extraction.
Handles malformed markdown, nested blocks, and edge cases.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

# Try to use mistletoe for advanced parsing
try:
    import mistletoe
    from mistletoe.block_token import CodeFence
    HAS_MISTLETOE = True
except ImportError:
    HAS_MISTLETOE = False


class ParserState(Enum):
    """State machine states for code block parsing."""
    NORMAL = "normal"
    IN_CODE_BLOCK = "in_code_block"


@dataclass
class CodeBlock:
    """Represents an extracted code block."""
    code: str
    language: str
    start_line: int
    end_line: int


def extract_code_blocks_regex(text: str) -> List[CodeBlock]:
    """
    Fallback regex-based extraction for when mistletoe is unavailable.
    
    More robust than simple regex:
    - Handles triple backticks with language specifier
    - Ignores inline code
    - Tracks line numbers
    """
    blocks: List[CodeBlock] = []
    lines = text.split('\n')
    
    state = ParserState.NORMAL
    current_block: List[str] = []
    block_start = 0
    block_language = ""
    fence_char = '`'
    fence_count = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if state == ParserState.NORMAL:
            # Check for opening fence (``` or ~~~)
            if stripped.startswith('```') or stripped.startswith('~~~'):
                fence_char = stripped[0]
                fence_count = len(stripped) - len(stripped.lstrip(fence_char))
                
                if fence_count >= 3:
                    state = ParserState.IN_CODE_BLOCK
                    block_start = i + 1
                    
                    # Extract language specifier
                    remainder = stripped[fence_count:].strip()
                    block_language = remainder.split()[0] if remainder else ""
                    current_block = []
                    
        elif state == ParserState.IN_CODE_BLOCK:
            # Check for closing fence
            if stripped.startswith(fence_char * fence_count) and \
               len(stripped.rstrip(fence_char)) <= len(stripped) - fence_count:
                # Found closing fence
                state = ParserState.NORMAL
                
                code = '\n'.join(current_block)
                if code.strip():
                    blocks.append(CodeBlock(
                        code=code,
                        language=block_language,
                        start_line=block_start,
                        end_line=i,
                    ))
                current_block = []
            else:
                current_block.append(line)
    
    return blocks


def extract_code_blocks_mistletoe(text: str) -> List[CodeBlock]:
    """
    Use mistletoe for reliable markdown parsing.
    
    This handles edge cases that regex can miss:
    - Indented code blocks
    - Escaped backticks
    - Nested structures
    """
    if not HAS_MISTLETOE:
        return extract_code_blocks_regex(text)
    
    blocks: List[CodeBlock] = []
    
    with mistletoe.Document(text) as doc:
        for token in doc.children:
            if isinstance(token, CodeFence):
                blocks.append(CodeBlock(
                    code=token.children[0].content if token.children else "",
                    language=token.language or "",
                    start_line=getattr(token, 'line_number', 0),
                    end_line=getattr(token, 'line_number', 0),
                ))
    
    return blocks


def extract_python_code(text: str) -> List[str]:
    """
    Extract Python code blocks from markdown text.
    
    Filters for Python language and returns just the code strings.
    
    Args:
        text: Markdown text containing code blocks
        
    Returns:
        List of Python code strings
    """
    blocks = extract_code_blocks_mistletoe(text)
    
    python_codes: List[str] = []
    for block in blocks:
        # Accept python, py, or unspecified language
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
