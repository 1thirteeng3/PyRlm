Request for Comments (RFC-002): Hardening e Refatoração Arquitetural do RLM-PYTHON

Status: PROPOSTO
Versão: 2.0.0-draft
Severidade: CRÍTICA (Tier 0)
Contexto: Transição de segurança baseada em aplicação (AST) para segurança baseada em kernel (OS-Level Isolation) e mitigação de vazamento de dados.

1. Resumo Executivo e Motivação

A versão atual (v1.0.0) do rlm-python opera sob um modelo de ameaça otimista, confiando na análise estática de código (AST) para impedir execuções maliciosas. Esta abordagem é insuficiente para ambientes de produção hostis. Python é uma linguagem dinâmica demais para ser sanitizada estaticamente.

Este documento detalha a implementação técnica minuciosa para migrar a segurança para o nível do Sistema Operacional (gVisor/Seccomp), implementar filtros de saída (Egress Filtering) para prevenir exfiltração de dados e introduzir uma abstração de memória eficiente (ContextHandle).

2. Trilha 1: Isolamento de Runtime (Runtime Hardening)

Objetivo: Assumir que o código será malicioso e garantir que o container seja uma prisão inescapável.

2.1. Implementação do Runtime gVisor (runsc)

O runtime padrão do Docker (runc) compartilha o kernel do host. Vulnerabilidades de kernel (ex: Dirty Pipe) permitem escape de container. O gVisor intercepta syscalls no userspace, isolando efetivamente o kernel.

2.1.1. Alterações em core/repl/docker.py

A classe DockerSandbox deve ser modificada para aceitar configurações de runtime dinâmicas.

Arquivo Alvo: src/rlm/core/repl/docker.py

Modificação na Assinatura __init__:
Adicionar parâmetros runtime: str e security_opt: List[str].

Lógica de Detecção de Runtime:
Antes de instanciar o container, o sistema deve verificar se o runtime runsc está disponível no daemon Docker.

# Lógica pseudo-código para validação
docker_info = client.info()
available_runtimes = docker_info.get("Runtimes", {})

if "runsc" in available_runtimes:
    runtime_config = "runsc"
else:
    logger.warning("gVisor (runsc) não detectado. Caindo para isolamento Seccomp Estrito.")
    runtime_config = "runc"
    # Carregar perfil seccomp.json restritivo


Parâmetros de Execução do Container:
A chamada client.containers.run deve incluir explicitamente:

runtime=runtime_config

ipc_mode="none" (Desabilita Inter-Process Communication compartilhado)

security_opt=["no-new-privileges:true"] (Impede escalada de privilégios via setuid)

2.2. Nullificação de Rede (Network Isolation)

O agente deve ser incapaz de exfiltrar dados via TCP/UDP.

Implementação:
Na chamada containers.run() em core/repl/docker.py:

Setar network_mode="none".

Impacto Crítico: Isso impede pip install dentro do código do agente.

Mitigação: Todas as dependências (pandas, numpy, scipy, scikit-learn) devem estar pré-instaladas na imagem base RLM_SANDBOX_IMAGE.

Verificação: Criar um teste unitário que tenta fazer urllib.request.urlopen("http://google.com") e asseverar que lança URLError instantâneo (não timeout).

2.3. Controle de Recursos (Cgroups v2)

Prevenção de ataques de Negação de Serviço (DoS) que visam exaurir recursos do host.

Configuração de Limites (core/repl/docker.py):

mem_limit="512m": Impede alocação massiva de memória.

memswap_limit="512m": Desabilita swap (swap permite escrita em disco do host).

pids_limit=50: Impede Fork Bombs (while True: os.fork()).

cpu_quota=100000 (1 vCPU): Impede sequestro de CPU para mineração de cripto.

2.4. Remoção do AST (The Great Purge)

Arquivos para Deleção: src/rlm/core/security/ast_validator.py.

Alteração em core/orchestrator.py:
Remover o passo validate_code(code_block) do método step(). O código bruto vai direto para o container blindado.

3. Trilha 2: Prevenção de Vazamento de Dados (Egress Filtering)

Objetivo: Impedir que o LLM "leia" o contexto e o envie de volta para a nuvem (OpenAI/Anthropic) via logs (stdout).

3.1. Filtro de Entropia (Shannon Entropy)

Dados sensíveis (chaves criptográficas, zips, binários) possuem alta entropia. Texto natural possui baixa entropia.

Novo Módulo: src/rlm/security/egress.py

Algoritmo:

import math
from collections import Counter

def calculate_shannon_entropy(data: str) -> float:
    if not data: return 0
    entropy = 0
    for x in Counter(data).values():
        p_x = x / len(data)
        entropy -= p_x * math.log2(p_x)
    return entropy


Regra de Negócio:
Se entropy > 4.5 E len(data) > 256:
Substituir saída por [SECURITY REDACTION: High Entropy Data Detected - Potential Secret Leak].

3.2. Detecção de "Papagaio" (Echo Detection)

Impede que o LLM imprima o contexto bruto (ex: print(context)).

Implementação em src/rlm/security/egress.py:

Manter um fingerprint (hash ou amostra) do contexto carregado.

Usar algoritmo de similaridade (Levenshtein rápido ou Jaccard sobre n-grams) para comparar stdout com context.

Se similarity(stdout, context_chunk) > 0.8:
Bloquear retorno e levantar DataLeakageError("Do not print raw context. Summarize it.").

3.3. Governador de Saída (Output Governor)

Lógica de Truncamento Inteligente:
O LLM precisa ver o erro (fim do log) e o cabeçalho (início). O meio é irrelevante.

Configuração: MAX_STDOUT_BYTES = 4000.

Implementação:

if len(stdout) > MAX_STDOUT_BYTES:
    head = stdout[:1000]
    tail = stdout[-3000:]
    stdout = f"{head}\n... [TRUNCATED {len(stdout)-4000} bytes] ...\n{tail}"


4. Trilha 3: Abstração de Memória (ContextHandle)

Objetivo: Evitar OOM (Out Of Memory) no container e facilitar manipulação de Big Data pelo LLM.

4.1. Design da Classe ContextHandle

Esta classe será injetada no globals() do REPL, substituindo a variável context string pura.

Localização: src/rlm/core/memory/handle.py (será copiada para dentro do container no startup).

API Pública (Disponível para o LLM):

class ContextHandle:
    def __init__(self, filepath: str):
        self._filepath = filepath
        self._file_size = os.path.getsize(filepath)

    @property
    def size(self) -> int:
        """Retorna tamanho total em bytes."""
        return self._file_size

    def read(self, start: int, length: int) -> str:
        """Lê um chunk específico (Seek + Read)."""
        with open(self._filepath, 'r', encoding='utf-8') as f:
            f.seek(start)
            return f.read(length)

    def search(self, pattern: str, max_results: int = 5) -> List[Tuple[int, str]]:
        """Retorna lista de (offset, match_string) usando regex sem carregar tudo."""
        # Implementação iterativa linha a linha para memória constante O(1)
        pass

    def snippet(self, offset: int, window: int = 500) -> str:
        """Retorna contexto ao redor de um offset."""
        start = max(0, offset - window // 2)
        return self.read(start, window)


4.2. Mapeamento de Volume

Alteração no Docker: O arquivo de contexto no host deve ser montado como volume Read-Only no container.

volumes={host_path: {'bind': '/mnt/context_data', 'mode': 'ro'}}

Inicialização: O script de boot do container instancia ctx = ContextHandle('/mnt/context_data').

4.3. Refatoração do System Prompt

Atualizar src/rlm/prompt_templates/system.py para ensinar a nova API:

"You have access to a ctx object. DO NOT try to read the whole file.
Use ctx.search(regex) to find patterns.
Use ctx.snippet(offset) to read specific sections."

5. Trilha 4: Configuração e Comercial

Objetivo: Profissionalização da gestão de configurações.

5.1. Migração para Pydantic Settings

Novo Arquivo: src/rlm/config/settings.py

Schema Rigoroso:

from pydantic_settings import BaseSettings

class RLMSettings(BaseSettings):
    # API Configs
    api_provider: Literal["openai", "anthropic", "google"]
    api_key: SecretStr

    # Security Configs
    execution_mode: Literal["docker", "local"] = "docker"
    docker_runtime: str = "runc" # Default seguro, tenta runsc auto

    # Safety Configs
    cost_limit_usd: float = 5.0
    max_recursion_depth: int = 3

    class Config:
        env_prefix = "RLM_"
        env_file = ".env"


5.2. Provider de Preços Externo

Remover: Dicionário PRICING_DEFAULTS de utils/cost.py.

Novo Arquivo: src/rlm/data/pricing.json.

Lógica de Carregamento:
Ao iniciar, o BudgetManager tenta carregar pricing.json do diretório de configuração do usuário (~/.rlm/ ou %APPDATA%). Se não existir, usa um fallback mínimo embutido, mas emite um alerta de "Preços Desatualizados".

6. Plano de Verificação (QA & Red Teaming)

A release 2.0.0 só será aprovada se passar nos seguintes cenários de ataque:

Ataque de Rede: Código tenta socket.connect(('1.1.1.1', 80)).

Resultado Esperado: OSError: [Errno 101] Network is unreachable.

Ataque de Disco: Código tenta open('/etc/shadow', 'r').

Resultado Esperado: PermissionError (devido a mapeamento de volume e user namespace) ou arquivo inexistente.

Ataque de Memória: Código tenta a = 'a' * 10**9 (1GB String).

Resultado Esperado: Container morre com OOMKilled; SandboxHandler captura o exit code 137 e retorna "Memory Limit Exceeded" para o LLM.

Vazamento de Chave: Código tenta print(ctx.read(0, 1000)) onde o contexto contém PRIVATE KEY.

Resultado Esperado: Output substituído por tags de <REDACTED> devido à alta entropia.

Autores: Equipe de Engenharia de Segurança & Arquitetura RLM
Data: 21/01/2026