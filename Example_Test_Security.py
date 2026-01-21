# tests/security/test_v2_hardening.py
import pytest
from rlm.core.repl.docker import DockerSandbox
from rlm.core.exceptions import SecurityViolationError

@pytest.mark.security
class TestV2Hardening:
    
    def test_network_isolation(self):
        """
        Verifica se a rede está realmente inoperante (network_mode='none').
        Tenta conectar ao IP do Google DNS (8.8.8.8).
        """
        sandbox = DockerSandbox(image="python:3.10-slim", network_disabled=True)
        code = """
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    s.connect(("8.8.8.8", 53))
    print("CONECTADO")
except OSError as e:
    print(f"BLOQUEADO: {e}")
except Exception as e:
    print(f"ERRO: {e}")
        """
        result = sandbox.execute(code)
        # O erro esperado para rede desligada é 'Network is unreachable' ou similar
        assert "Network is unreachable" in result.stdout or "BLOQUEADO" in result.stdout
        assert "CONECTADO" not in result.stdout

    def test_context_mmap_usage(self, tmp_path):
        """
        Verifica se o ContextHandle consegue ler um arquivo sem carregar tudo na RAM.
        Cria um arquivo dummy de 100MB e lê o meio.
        """
        # Setup: Criar arquivo grande
        f_path = tmp_path / "big_context.txt"
        with open(f_path, "wb") as f:
            f.seek(100 * 1024 * 1024 - 1) # 100MB
            f.write(b"\0")
            
        # Escrever um 'segredo' no meio
        with open(f_path, "r+b") as f:
            f.seek(50 * 1024 * 1024)
            f.write(b"SEGREDO_NO_MEIO")

        # Código do agente usando a nova API
        code = f"""
from rlm.core.memory.handle import ContextHandle
ctx = ContextHandle('{str(f_path)}')
print(ctx.read_window(50 * 1024 * 1024, radius=10))
        """
        
        # O sandbox precisa montar esse arquivo. 
        # (Assumindo que o mock do sandbox suporte montagem dinâmica para este teste)
        sandbox = DockerSandbox(image="python:3.10-slim")
        result = sandbox.execute(code, context_mount=str(f_path))
        
        assert "SEGREDO" in result.stdout