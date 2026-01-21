"""Tests for egress filtering and security sanitization."""

import pytest

from rlm.security.egress import (
    EgressFilter,
    calculate_shannon_entropy,
    calculate_similarity,
    detect_secrets,
    sanitize_output,
)


class TestShannonEntropy:
    """Tests for Shannon entropy calculation."""

    def test_empty_string(self):
        """Empty string should have zero entropy."""
        assert calculate_shannon_entropy("") == 0.0

    def test_single_char(self):
        """Repeated single character should have zero entropy."""
        assert calculate_shannon_entropy("aaaaaaaaaa") == 0.0

    def test_natural_text_low_entropy(self):
        """Natural language text should have low-medium entropy."""
        text = "The quick brown fox jumps over the lazy dog."
        entropy = calculate_shannon_entropy(text)
        assert 3.5 < entropy < 4.5

    def test_random_high_entropy(self):
        """Random-looking strings should have high entropy."""
        # Simulated API key
        text = "sk-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"
        entropy = calculate_shannon_entropy(text)
        assert entropy > 4.0

    def test_base64_high_entropy(self):
        """Base64 encoded data should have high entropy."""
        text = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        entropy = calculate_shannon_entropy(text)
        assert entropy > 4.0  # Base64 typically has entropy around 4.3


class TestSimilarity:
    """Tests for text similarity calculation."""

    def test_identical_strings(self):
        """Identical strings should have similarity of 1.0."""
        similarity = calculate_similarity("hello world", "hello world")
        assert similarity == 1.0

    def test_completely_different(self):
        """Completely different strings should have low similarity."""
        similarity = calculate_similarity("aaa bbb ccc", "xxx yyy zzz")
        assert similarity < 0.2

    def test_partial_overlap(self):
        """Partially overlapping strings should have medium similarity."""
        similarity = calculate_similarity(
            "the quick brown fox",
            "the quick brown dog",
        )
        assert 0.5 < similarity < 0.9

    def test_empty_strings(self):
        """Empty strings should have zero similarity."""
        assert calculate_similarity("", "hello") == 0.0
        assert calculate_similarity("hello", "") == 0.0
        assert calculate_similarity("", "") == 0.0


class TestSecretDetection:
    """Tests for secret pattern detection."""

    def test_detect_api_key(self):
        """Should detect API key patterns."""
        text = 'api_key = "sk-1234567890abcdefghij"'
        secrets = detect_secrets(text)
        assert len(secrets) > 0
        assert any("api_key" in s[0] for s in secrets)

    def test_detect_aws_key(self):
        """Should detect AWS access key pattern."""
        text = "AKIAIOSFODNN7EXAMPLE"
        secrets = detect_secrets(text)
        assert len(secrets) > 0
        assert any("aws" in s[0] for s in secrets)

    def test_detect_private_key(self):
        """Should detect private key headers."""
        text = "-----BEGIN RSA PRIVATE KEY-----"
        secrets = detect_secrets(text)
        assert len(secrets) > 0
        assert any("private_key" in s[0] for s in secrets)

    def test_detect_jwt(self):
        """Should detect JWT tokens."""
        text = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        secrets = detect_secrets(text)
        assert len(secrets) > 0
        assert any("jwt" in s[0] for s in secrets)

    def test_no_false_positives_normal_text(self):
        """Should not flag normal text as secrets."""
        text = "Hello, this is a normal message about the weather."
        secrets = detect_secrets(text)
        assert len(secrets) == 0


class TestEgressFilter:
    """Tests for the EgressFilter class."""

    def test_filter_high_entropy(self):
        """Should redact high entropy data."""
        filter_instance = EgressFilter()
        # Create a string with high entropy (many random chars)
        high_entropy_output = "x" * 50 + "".join(
            chr(i % 94 + 33) for i in range(300)
        )
        result = filter_instance.filter(high_entropy_output)
        assert "REDACTION" in result or "Entropy" in result

    def test_filter_context_echo(self):
        """Should detect context echoing."""
        context = "This is the secret context that should not be leaked."
        filter_instance = EgressFilter(context=context)

        # Try to leak the context
        output = "This is the secret context that should not be leaked."
        result = filter_instance.filter(output)
        assert "REDACTION" in result or "Echo" in result

    def test_truncate_long_output(self):
        """Should truncate very long output."""
        filter_instance = EgressFilter(max_output_bytes=1000)
        long_output = "x" * 5000
        result = filter_instance.filter(long_output)
        assert len(result) < 5000
        assert "TRUNCATED" in result

    def test_pass_through_normal_output(self):
        """Should not modify normal, safe output."""
        filter_instance = EgressFilter()
        normal_output = "Result: 42\nCalculation complete."
        result = filter_instance.filter(normal_output)
        assert result == normal_output


class TestSanitizeOutput:
    """Tests for the convenience sanitize_output function."""

    def test_sanitize_with_context(self):
        """Should sanitize with context protection."""
        context = "Secret data here"
        output = "Secret data here"  # Echo attack
        result = sanitize_output(output, context=context)
        assert result != output  # Should be modified

    def test_sanitize_without_context(self):
        """Should work without context."""
        output = "Normal output"
        result = sanitize_output(output)
        assert result == output

    def test_raise_on_leak(self):
        """Should raise exception when configured."""
        from rlm.core.exceptions import DataLeakageError

        # This should raise due to the secret pattern
        with pytest.raises(DataLeakageError):
            sanitize_output(
                "-----BEGIN RSA PRIVATE KEY-----",
                raise_on_leak=True,
            )
