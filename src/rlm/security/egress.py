"""
Egress Filtering Module.

This module implements security filters to prevent data exfiltration through
code execution output. It detects:
1. High entropy data (potential secrets, API keys, private keys)
2. Context echo attacks (printing raw context back)
3. Oversized output (truncation with smart head/tail preservation)
"""

import hashlib
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Optional

from rlm.config.settings import settings
from rlm.core.exceptions import DataLeakageError

logger = logging.getLogger(__name__)


# Known secret patterns
SECRET_PATTERNS = [
    # API Keys
    r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?[\w-]{20,}",
    # AWS
    r"(?i)AKIA[0-9A-Z]{16}",
    r"(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*['\"]?[\w/+]{40}",
    # Private Keys
    r"-----BEGIN\s+(RSA|DSA|EC|OPENSSH|PGP)\s+PRIVATE\s+KEY-----",
    # JWT
    r"eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_.+/=]*",
    # Generic tokens
    r"(?i)(secret|token|password|passwd|pwd)\s*[:=]\s*['\"]?[\w-]{16,}",
    # Bearer tokens
    r"(?i)bearer\s+[a-zA-Z0-9\-_.~+/]+=*",
]


def calculate_shannon_entropy(data: str) -> float:
    """
    Calculate Shannon entropy of a string.

    Higher entropy indicates more randomness - potential secrets or
    encoded binary data.

    Args:
        data: String to analyze

    Returns:
        Shannon entropy value (typically 0-8 for ASCII text)
        - 0-2: Very low entropy (repetitive)
        - 2-4: Low entropy (natural language)
        - 4-5: Medium entropy (code, mixed content)
        - 5-8: High entropy (secrets, binary, compressed)
    """
    if not data:
        return 0.0

    entropy = 0.0
    counter = Counter(data)
    length = len(data)

    for count in counter.values():
        if count > 0:
            probability = count / length
            entropy -= probability * math.log2(probability)

    return entropy


def calculate_similarity(s1: str, s2: str, ngram_size: int = 3) -> float:
    """
    Calculate Jaccard similarity between two strings using n-grams.

    This is used to detect "echo attacks" where the LLM prints
    the raw context back.

    Args:
        s1: First string
        s2: Second string
        ngram_size: Size of n-grams to use

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not s1 or not s2:
        return 0.0

    # Generate n-grams
    def get_ngrams(s: str) -> set:
        s = s.lower()
        return {s[i : i + ngram_size] for i in range(len(s) - ngram_size + 1)}

    ngrams1 = get_ngrams(s1)
    ngrams2 = get_ngrams(s2)

    if not ngrams1 or not ngrams2:
        return 0.0

    intersection = len(ngrams1 & ngrams2)
    union = len(ngrams1 | ngrams2)

    return intersection / union if union > 0 else 0.0


def detect_secrets(text: str) -> list[tuple[str, str]]:
    """
    Detect potential secrets in text using pattern matching.

    Args:
        text: Text to scan

    Returns:
        List of (pattern_name, matched_text) tuples
    """
    matches = []
    pattern_names = [
        "api_key",
        "aws_access_key",
        "aws_secret",
        "private_key",
        "jwt",
        "generic_secret",
        "bearer_token",
    ]

    for pattern, name in zip(SECRET_PATTERNS, pattern_names):
        for match in re.finditer(pattern, text):
            # Truncate match for logging
            matched = match.group()[:50] + "..." if len(match.group()) > 50 else match.group()
            matches.append((name, matched))

    return matches


@dataclass
class EgressFilter:
    """
    Filter for sanitizing code execution output.

    Implements multiple layers of protection:
    1. Entropy detection for secrets
    2. Pattern matching for known secret formats
    3. Context similarity detection
    4. Output size limiting
    """

    entropy_threshold: float = 4.5
    min_entropy_length: int = 256
    similarity_threshold: float = 0.8
    max_output_bytes: int = 4000
    context_fingerprint: Optional[str] = None
    context_sample: Optional[str] = None

    def __init__(
        self,
        context: Optional[str] = None,
        entropy_threshold: Optional[float] = None,
        similarity_threshold: Optional[float] = None,
        max_output_bytes: Optional[int] = None,
    ) -> None:
        """
        Initialize the egress filter.

        Args:
            context: The context/input data to protect from leakage
            entropy_threshold: Override default entropy threshold
            similarity_threshold: Override default similarity threshold
            max_output_bytes: Override default output size limit
        """
        self.entropy_threshold = entropy_threshold or settings.entropy_threshold
        self.min_entropy_length = settings.min_entropy_length
        self.similarity_threshold = similarity_threshold or settings.similarity_threshold
        self.max_output_bytes = max_output_bytes or settings.max_stdout_bytes

        if context:
            self.context_fingerprint = hashlib.sha256(context.encode()).hexdigest()
            # Store sample chunks for similarity comparison
            self.context_sample = context[:2000] if len(context) > 2000 else context

    def check_entropy(self, text: str) -> tuple[bool, float]:
        """
        Check if text has suspiciously high entropy.

        Args:
            text: Text to check

        Returns:
            Tuple of (is_suspicious, entropy_value)
        """
        if len(text) < self.min_entropy_length:
            return False, 0.0

        entropy = calculate_shannon_entropy(text)
        is_high = entropy > self.entropy_threshold

        if is_high:
            logger.warning(f"High entropy detected: {entropy:.2f} (threshold: {self.entropy_threshold})")

        return is_high, entropy

    def check_context_echo(self, output: str) -> tuple[bool, float]:
        """
        Check if output is echoing the context (data exfiltration).

        Args:
            output: Output to check

        Returns:
            Tuple of (is_echo, similarity_score)
        """
        if not self.context_sample:
            return False, 0.0

        similarity = calculate_similarity(output, self.context_sample)
        is_echo = similarity > self.similarity_threshold

        if is_echo:
            logger.warning(
                f"Context echo detected: similarity {similarity:.2f} "
                f"(threshold: {self.similarity_threshold})"
            )

        return is_echo, similarity

    def check_secrets(self, text: str) -> list[tuple[str, str]]:
        """
        Check for known secret patterns.

        Args:
            text: Text to check

        Returns:
            List of detected secrets (pattern_name, redacted_match)
        """
        return detect_secrets(text)

    def truncate_output(self, text: str) -> str:
        """
        Truncate output while preserving head and tail (most useful parts).

        Args:
            text: Text to truncate

        Returns:
            Truncated text with indicator
        """
        if len(text) <= self.max_output_bytes:
            return text

        # Preserve first 1KB and last 3KB (errors usually at the end)
        head_size = 1000
        tail_size = 3000
        truncated = len(text) - head_size - tail_size

        head = text[:head_size]
        tail = text[-tail_size:]

        return f"{head}\n\n... [TRUNCATED {truncated} bytes] ...\n\n{tail}"

    def filter(
        self,
        output: str,
        raise_on_leak: bool = False,
    ) -> str:
        """
        Apply all egress filters to output.

        Args:
            output: Raw output to filter
            raise_on_leak: Whether to raise DataLeakageError on detection

        Returns:
            Sanitized output

        Raises:
            DataLeakageError: If raise_on_leak is True and leakage is detected
        """
        if not output:
            return output

        redactions = []

        # Check for secrets
        secrets = self.check_secrets(output)
        if secrets:
            if raise_on_leak:
                raise DataLeakageError(
                    message="Secrets detected in output",
                    leak_type="secret_pattern",
                    details={"patterns": [s[0] for s in secrets]},
                )
            for pattern_name, matched in secrets:
                redactions.append(f"[REDACTED: {pattern_name}]")
                # Remove the matched content
                output = re.sub(re.escape(matched), f"[REDACTED: {pattern_name}]", output)

        # Check for high entropy
        is_high_entropy, entropy = self.check_entropy(output)
        if is_high_entropy:
            if raise_on_leak:
                raise DataLeakageError(
                    message="High entropy data detected - potential secret leak",
                    leak_type="high_entropy",
                    details={"entropy": entropy},
                )
            output = f"[SECURITY REDACTION: High Entropy Data Detected - Potential Secret Leak]\n(Entropy: {entropy:.2f})"

        # Check for context echo
        is_echo, similarity = self.check_context_echo(output)
        if is_echo:
            if raise_on_leak:
                raise DataLeakageError(
                    message="Do not print raw context. Summarize it.",
                    leak_type="context_echo",
                    details={"similarity": similarity},
                )
            output = f"[SECURITY REDACTION: Context Echo Detected]\nDo not print raw context data. Use ctx.search() and ctx.snippet() to extract specific information."

        # Truncate if needed
        output = self.truncate_output(output)

        if redactions:
            logger.info(f"Egress filter applied {len(redactions)} redactions")

        return output


def sanitize_output(
    output: str,
    context: Optional[str] = None,
    raise_on_leak: bool = False,
) -> str:
    """
    Convenience function to sanitize code execution output.

    Args:
        output: Raw output from code execution
        context: Optional context data to protect from leakage
        raise_on_leak: Whether to raise exception on detected leakage

    Returns:
        Sanitized output
    """
    filter_instance = EgressFilter(context=context)
    return filter_instance.filter(output, raise_on_leak=raise_on_leak)
