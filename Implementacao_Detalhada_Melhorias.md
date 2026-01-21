Plano de Implementação Detalhado: Melhorias Críticas RLM-Python

Este documento expande o RFC-002, fornecendo diretrizes de implementação passo a passo para desenvolvedores.

Fase 1: Hardening do Ambiente de Execução (Semana 1)

Passo 1.1: Atualizar Dependências

Modificar pyproject.toml ou requirements.txt para incluir novas libs necessárias para a refatoração de configuração.

[project.dependencies]
docker = "^7.0.0"
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"


Passo 1.2: Refatorar DockerSandbox (core/repl/docker.py)

A prioridade é implementar o suporte a runsc e isolamento de rede.

Código de Referência para Implementação:

import docker
from docker.errors import DockerException
import logging

logger = logging.getLogger(__name__)

class DockerSandbox:
    def __init__(self, image: str, timeout: int = 30):
        self.client = docker.from_env()
        self.image = image
        self.timeout = timeout
        self.runtime = self._detect_secure_runtime()

    def _detect_secure_runtime(self) -> str:
        """Detecta se gVisor (runsc) está disponível."""
        try:
            info = self.client.info()
            runtimes = info.get("Runtimes", {})
            if "runsc" in runtimes:
                logger.info("Runtime seguro 'runsc' (gVisor) detectado e ativado.")
                return "runsc"
            else:
                logger.warning("AVISO DE SEGURANÇA: 'runsc' não encontrado. Usando isolamento padrão 'runc'.")
                return "runc"
        except Exception as e:
            logger.error(f"Falha ao detectar runtimes Docker: {e}")
            return "runc"

    def execute(self, code: str, context_mount_path: str = None) -> dict:
        """
        Executa código com isolamento máximo.
        Args:
            code: Código Python a executar.
            context_mount_path: Caminho no host para o arquivo de contexto (para bind mount).
        """
        volumes = {}
        if context_mount_path:
            # Monta o contexto como Read-Only em /mnt/context
            volumes[context_mount_path] = {'bind': '/mnt/context', 'mode': 'ro'}

        try:
            container = self.client.containers.run(
                self.image,
                command=f"python3 -c {shlex.quote(code)}",
                detach=True,
                # SEGURANÇA: Isolamento de Rede
                network_mode="none", 
                # SEGURANÇA: Runtime gVisor ou padrão
                runtime=self.runtime,
                # SEGURANÇA: Limites de Recursos
                mem_limit="512m",
                memswap_limit="512m",
                nano_cpus=1000000000, # 1 CPU
                pids_limit=50,
                # SEGURANÇA: Privilégios
                security_opt=["no-new-privileges:true"],
                # IO: Montagem de volumes
                volumes=volumes,
                # Limpeza automática
                remove=True # Cuidado com debug, talvez manter False e remover manual
            )
            
            # ... lógica de wait e logs (implementar timeout manual aqui) ...
            
        except Exception as e:
            # ... tratamento de erro ...
            pass


Passo 1.3: Eliminar Validação AST

Apagar o arquivo src/rlm/core/security/ast_validator.py.

No src/rlm/core/orchestrator.py, remover a importação e a chamada ASTValidator.validate(code).

Atualizar os testes unitários que esperavam SecurityViolationError vindo do AST para esperar erros de ImportError ou OSError vindo da execução real do Docker (ou mocks correspondentes).

Fase 2: Gestão de Dados e Contexto (Semana 2-3)

Passo 2.1: Implementar ContextHandle

Criar o arquivo src/rlm/core/memory/handle.py. Este arquivo tem uma particularidade: ele precisa existir tanto no host (para tipagem/dev) quanto ser injetado dentro do container.

Estratégia de Injeção:
O conteúdo deste arquivo pode ser lido como string e prepended (anexado ao início) do código que o LLM gera antes de enviar para o Docker.

# src/rlm/core/memory/handle.py

import mmap
import os
import re
from typing import List, Tuple

class ContextHandle:
    def __init__(self, path: str = "/mnt/context"):
        self.path = path
        if not os.path.exists(path):
            raise FileNotFoundError(f"Context file not found at {path}")
        self._size = os.path.getsize(path)

    def search(self, pattern: str, chunk_size: int = 1024*1024) -> List[Tuple[int, str]]:
        """
        Busca regex no arquivo usando mmap para eficiência de memória.
        Retorna lista de (offset, match_string).
        """
        matches = []
        with open(self.path, "r+b") as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                # Nota: Regex em bytes para mmap
                bytes_pattern = pattern.encode('utf-8')
                for match in re.finditer(bytes_pattern, mm):
                    if len(matches) >= 10: break # Limite de segurança
                    try:
                        decoded = match.group().decode('utf-8')
                        matches.append((match.start(), decoded))
                    except UnicodeDecodeError:
                        continue # Ignora matches binários inválidos
        return matches

    def read_window(self, offset: int, radius: int = 500) -> str:
        """Lê texto ao redor de um offset seguro."""
        start = max(0, offset - radius)
        length = radius * 2
        with open(self.path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(start)
            return f.read(length)


Passo 2.2: Filtros de Saída (Egress)

No core/orchestrator.py, antes de adicionar a observação ao histórico:

# No método step() após receber output do sandbox
from rlm.security.egress import sanitize_output

# ... executa código ...
raw_output = sandbox_result.stdout

# Aplica sanitização
safe_output = sanitize_output(raw_output, context_sample=self.context_hash)

# Adiciona ao histórico
self.history.append({"role": "user", "content": f"Observation: {safe_output}"})


Implementar sanitize_output com verificação de entropia descrita no RFC.

Fase 3: Configuração (Semana 4)

Passo 3.1: Classe RLMConfig

Substituir o uso de os.getenv espalhado pelo código.

# src/rlm/config/main.py
from pydantic_settings import BaseSettings
from pydantic import Field

class RLMConfig(BaseSettings):
    api_key: str = Field(..., env="RLM_API_KEY")
    execution_mode: str = Field("docker", env="RLM_EXECUTION_MODE")
    
    # Pricing overrides (opcional, path para JSON)
    pricing_path: str = Field(None, env="RLM_PRICING_PATH")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Singleton global
settings = RLMConfig()


Passo 3.2: Refatoração de Uso

Procurar globalmente no projeto (Ctrl+Shift+F) por os.environ, os.getenv e substituir por settings.NOME_VARIAVEL.

Checklist de Validação Final

Antes de considerar a tarefa concluída:

[ ] Build Docker: A imagem base do sandbox deve ter as dependências instaladas (pip install pandas numpy ...) já que o container não terá rede. Atualizar Dockerfile do sandbox se ele existir, ou documentar qual imagem usar.

[ ] Testes de Regressão: Garantir que o fluxo "feliz" (perguntar "Qual a capital da França?") continua funcionando com a nova infraestrutura.

[ ] Testes de Carga: Rodar o sistema contra um arquivo de texto de 500MB para garantir que o mmap funciona e não estoura a RAM do container (limitada a 512MB).