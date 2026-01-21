"""
Security Hardening Tests (v2.0)

These tests validate the security measures implemented in RLM v2.0,
including network isolation, memory limits, and egress filtering.

These tests require Docker to be available and may take longer to run.
"""

import pytest

# Mark all tests in this module as security tests
pytestmark = [pytest.mark.security, pytest.mark.integration]


class TestNetworkIsolation:
    """Tests for network isolation in Docker sandbox."""

    @pytest.mark.skipif(
        not pytest.importorskip("docker", reason="Docker not available"),
        reason="Docker required",
    )
    def test_network_blocked(self):
        """
        Verifica se a rede está realmente inoperante (network_mode='none').
        Tenta conectar ao IP do Google DNS (8.8.8.8).
        """
        from rlm.core.repl.docker import DockerSandbox

        sandbox = DockerSandbox(image="python:3.11-slim")

        code = '''
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    s.connect(("8.8.8.8", 53))
    print("CONNECTED")
except OSError as e:
    print(f"BLOCKED: {e}")
except Exception as e:
    print(f"ERROR: {e}")
'''
        result = sandbox.execute(code)

        # O erro esperado para rede desligada é 'Network is unreachable' ou similar
        assert "Network is unreachable" in result.stdout or "BLOCKED" in result.stdout
        assert "CONNECTED" not in result.stdout

    @pytest.mark.skipif(
        not pytest.importorskip("docker", reason="Docker not available"),
        reason="Docker required",
    )
    def test_dns_blocked(self):
        """Test that DNS resolution is blocked."""
        from rlm.core.repl.docker import DockerSandbox

        sandbox = DockerSandbox(image="python:3.11-slim")

        code = '''
import socket
try:
    ip = socket.gethostbyname("google.com")
    print(f"RESOLVED: {ip}")
except socket.gaierror as e:
    print(f"BLOCKED: {e}")
except Exception as e:
    print(f"ERROR: {e}")
'''
        result = sandbox.execute(code)
        assert "BLOCKED" in result.stdout or "ERROR" in result.stdout
        assert "RESOLVED" not in result.stdout


class TestMemoryLimits:
    """Tests for memory limit enforcement."""

    @pytest.mark.skipif(
        not pytest.importorskip("docker", reason="Docker not available"),
        reason="Docker required",
    )
    def test_memory_bomb_killed(self):
        """
        Código tenta alocar 1GB de memória.
        Resultado Esperado: Container morre com OOMKilled.
        """
        from rlm.core.repl.docker import DockerSandbox

        sandbox = DockerSandbox(image="python:3.11-slim")

        code = '''
# Try to allocate 1GB string
a = "a" * (1024 * 1024 * 1024)
print("ALLOCATED")
'''
        result = sandbox.execute(code)

        # Either OOM killed or error
        assert result.oom_killed or result.exit_code != 0 or "MemoryError" in result.stdout
        assert "ALLOCATED" not in result.stdout


class TestFileSystemIsolation:
    """Tests for file system isolation."""

    @pytest.mark.skipif(
        not pytest.importorskip("docker", reason="Docker not available"),
        reason="Docker required",
    )
    def test_sensitive_file_access_blocked(self):
        """
        Código tenta ler /etc/shadow.
        Resultado Esperado: PermissionError ou arquivo inexistente.
        """
        from rlm.core.repl.docker import DockerSandbox

        sandbox = DockerSandbox(image="python:3.11-slim")

        code = '''
try:
    with open("/etc/shadow", "r") as f:
        print(f"CONTENTS: {f.read()[:100]}")
except PermissionError as e:
    print(f"BLOCKED: {e}")
except FileNotFoundError as e:
    print(f"NOT_FOUND: {e}")
except Exception as e:
    print(f"ERROR: {e}")
'''
        result = sandbox.execute(code)

        assert "BLOCKED" in result.stdout or "NOT_FOUND" in result.stdout or "ERROR" in result.stdout
        assert "CONTENTS" not in result.stdout


class TestModuleBlocking:
    """Tests for dangerous module blocking."""

    @pytest.mark.skipif(
        not pytest.importorskip("docker", reason="Docker not available"),
        reason="Docker required",
    )
    def test_subprocess_blocked(self):
        """Test that subprocess module is blocked."""
        from rlm.core.repl.docker import DockerSandbox

        sandbox = DockerSandbox(image="python:3.11-slim")

        code = '''
try:
    import subprocess
    result = subprocess.run(["ls", "/"], capture_output=True)
    print(f"EXECUTED: {result.stdout}")
except ImportError as e:
    print(f"BLOCKED: {e}")
except Exception as e:
    print(f"ERROR: {e}")
'''
        result = sandbox.execute(code)
        assert "BLOCKED" in result.stdout


class TestContextMmapUsage:
    """Tests for memory-efficient context handling."""

    def test_context_mmap_usage(self, tmp_path):
        """
        Verifica se o ContextHandle consegue ler um arquivo sem carregar tudo na RAM.
        Cria um arquivo de 10MB e lê o meio.
        """
        from rlm.core.memory.handle import ContextHandle

        # Setup: Criar arquivo grande
        f_path = tmp_path / "big_context.txt"
        with open(f_path, "wb") as f:
            # Write 10MB
            f.seek(10 * 1024 * 1024 - 1)
            f.write(b"\0")

        # Escrever um 'segredo' no meio
        with open(f_path, "r+b") as f:
            f.seek(5 * 1024 * 1024)
            f.write(b"SECRET_IN_MIDDLE")

        # Test reading with ContextHandle
        ctx = ContextHandle(str(f_path))

        # Search should find the secret
        matches = ctx.search(r"SECRET_IN_MIDDLE")
        assert len(matches) > 0

        # Read window should return the content
        content = ctx.read_window(5 * 1024 * 1024, radius=20)
        assert "SECRET" in content

        ctx.close()


class TestEgressFiltering:
    """Tests for egress filtering of sensitive data."""

    def test_entropy_detection(self):
        """Test that high entropy data is detected."""
        from rlm.security.egress import calculate_shannon_entropy

        # API key-like string should have high entropy
        api_key = "sk-proj-a1B2c3D4e5F6g7H8i9J0kLmNoPqRsTuVwXyZ"
        entropy = calculate_shannon_entropy(api_key)
        assert entropy > 4.0

    def test_secret_pattern_detection(self):
        """Test that known secret patterns are detected."""
        from rlm.security.egress import detect_secrets

        # AWS access key
        text = "AKIAIOSFODNN7EXAMPLE"
        secrets = detect_secrets(text)
        assert len(secrets) > 0

        # Private key header
        text = "-----BEGIN RSA PRIVATE KEY-----"
        secrets = detect_secrets(text)
        assert len(secrets) > 0

    def test_context_echo_detection(self):
        """Test that context echoing is detected."""
        from rlm.security.egress import EgressFilter

        context = "This is sensitive context data that should not be leaked directly."
        filter_instance = EgressFilter(context=context)

        # Trying to echo the context should be detected
        is_echo, similarity = filter_instance.check_context_echo(context)
        assert is_echo
        assert similarity > 0.8
