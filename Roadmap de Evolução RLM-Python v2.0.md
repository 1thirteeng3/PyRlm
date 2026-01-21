Roadmap de Evolução RLM-Python v2.0

Este cronograma estima o esforço necessário para a refatoração completa, assumindo uma equipe de 2 engenheiros seniores.

Semana

Foco Principal

Atividades Chave

Entregáveis

Semana 1

Infraestrutura de Segurança

1. Configuração do ambiente Docker (gVisor).



2. Implementação do network_mode="none".



3. Remoção do módulo AST.



4. Atualização da imagem Docker base (pré-install deps).

- Módulo DockerSandbox blindado.



- Imagem Docker rlm-sandbox:v2.



- AST removido do codebase.

Semana 2

Proteção de Dados (DLP)

1. Desenvolvimento do algoritmo de Entropia.



2. Implementação do Filtro de Egressão no Orquestrador.



3. Testes com chaves falsas (canary tokens).

- Módulo rlm.security.egress.



- Testes de unidade para sanitização.



- Bloqueio de print(context).

Semana 3

Gestão de Memória

1. Implementação da classe ContextHandle (com mmap).



2. Alteração na montagem de volumes Docker.



3. Reescrita dos System Prompts para usar a nova API.

- API ContextHandle funcional.



- Prompts v2 otimizados.



- Suporte a arquivos > 1GB.

Semana 4

Configuração & Release

1. Migração para Pydantic Settings.



2. Externalização da tabela de preços.



3. Documentação técnica (atualizar PDF Diátaxis).



4. Release Candidate (v2.0.0-rc1).

- settings.py centralizado.



- pricing.json externo.



- Documentação atualizada.

Riscos e Mitigações

Risco

Probabilidade

Impacto

Mitigação

Incompatibilidade gVisor

Média

Alto

Manter fallback automático para runc com perfil Seccomp estrito já pronto.

LLM alucinar API do ContextHandle

Alta

Médio

Usar Few-Shot Prompting robusto no System Prompt com exemplos claros de uso da API.

Dependências Python faltando

Alta

Alto (Crash)

Criar uma imagem "fat" (rlm-sandbox-datascience) com as top 50 libs de DS pré-instaladas.