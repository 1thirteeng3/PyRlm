# RLM-Python 🔒🤖

**Recursive Language Model** - A secure Python library for LLM-driven code execution with Docker sandboxing, egress filtering, and memory-efficient context handling.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🌟 Features

- **🐳 Docker Sandbox Execution** - Execute untrusted code in isolated containers with gVisor support
- **🔐 OS-Level Security** - Network isolation, memory limits, process limits, privilege restrictions
- **🛡️ Egress Filtering** - Prevent data exfiltration via entropy detection and pattern matching
- **📚 Memory-Efficient Context** - Handle gigabyte-scale files with mmap-based `ContextHandle`
- **🤖 Multi-Provider LLM** - Support for OpenAI, Anthropic, and Google Gemini
- **💰 Budget Management** - Track API costs and enforce spending limits
- **📝 Typed & Tested** - Full type hints with comprehensive test coverage

## 🚀 Quick Start

### Installation

```bash
pip install rlm-python
```

Or install from source:

```bash
git clone https://github.com/rlm-python/rlm.git
cd rlm
pip install -e ".[dev]"
```

### Basic Usage

```python
from rlm import Orchestrator, settings

# Configure via environment variables or .env file
# RLM_API_KEY=sk-...
# RLM_API_PROVIDER=openai

# Create orchestrator
orchestrator = Orchestrator()

# Run a query with code execution
result = orchestrator.run("Calculate the first 10 prime numbers")

print(result.final_answer)
# [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]

print(f"Cost: ${result.budget_summary['total_spent_usd']:.4f}")
```

### With Context File

```python
from rlm import Orchestrator

orchestrator = Orchestrator()

# Query against a large document
result = orchestrator.run(
    "Find all email addresses mentioned in this document",
    context_path="/path/to/large_document.txt"
)

print(result.final_answer)
```

### Direct Sandbox Usage

```python
from rlm import DockerSandbox

sandbox = DockerSandbox()

result = sandbox.execute("""
import math
print(f"Pi = {math.pi}")
print(f"Factorial of 10 = {math.factorial(10)}")
""")

print(result.stdout)
# Pi = 3.141592653589793
# Factorial of 10 = 3628800
```

### Memory-Efficient Context Handling

```python
from rlm import ContextHandle

# Work with large files without loading into memory
with ContextHandle("/path/to/10gb_file.txt") as ctx:
    print(f"File size: {ctx.size_mb:.2f} MB")
    
    # Search using regex
    matches = ctx.search(r"API_KEY=\w+")
    
    for offset, match in matches:
        # Read context around match
        snippet = ctx.snippet(offset, window=200)
        print(f"Found at {offset}: {snippet}")
```

## ⚙️ Configuration

RLM is configured via environment variables (with `RLM_` prefix) or a `.env` file:

```bash
# API Configuration
RLM_API_PROVIDER=openai          # openai, anthropic, google
RLM_API_KEY=sk-...               # Your API key
RLM_MODEL_NAME=gpt-4o            # Model to use

# Execution Configuration  
RLM_EXECUTION_MODE=docker        # docker or local (dev only)
RLM_DOCKER_RUNTIME=auto          # auto, runsc, or runc
RLM_EXECUTION_TIMEOUT=30         # Seconds

# Safety Limits
RLM_COST_LIMIT_USD=5.0           # Max spending per session
RLM_MAX_RECURSION_DEPTH=5        # Max code execution iterations

# Security Settings
RLM_MEMORY_LIMIT=512m            # Container memory limit
RLM_NETWORK_ENABLED=false        # Network access (DANGEROUS if true)
RLM_ENTROPY_THRESHOLD=4.5        # Secret detection threshold
```

## 🔒 Security Architecture

RLM v2.0 implements **defense in depth** with multiple security layers:

### 1. Runtime Isolation
- **gVisor (runsc)** - Intercepts syscalls in userspace, isolating from host kernel
- **Automatic fallback** - Falls back to runc with seccomp if gVisor unavailable

### 2. Network Isolation
- `network_mode="none"` - Container has no network access
- Prevents data exfiltration via HTTP/DNS

### 3. Resource Limits
- **Memory**: 512MB default (prevents OOM attacks)
- **PIDs**: 50 max (prevents fork bombs)
- **CPU**: 1 core quota (prevents crypto mining)

### 4. Egress Filtering
- **Shannon Entropy** - Detects high-entropy data (secrets, keys)
- **Pattern Matching** - Recognizes API keys, JWT, private keys
- **Context Echo** - Prevents printing raw context back

### 5. Privilege Restrictions
- `no-new-privileges` - Blocks privilege escalation
- `ipc_mode="none"` - Isolates IPC namespace

## 📊 API Reference

### Orchestrator

```python
class Orchestrator:
    def run(query: str, context_path: str = None) -> OrchestratorResult
    def chat(message: str) -> str
```

### DockerSandbox

```python
class DockerSandbox:
    def execute(code: str, context_mount: str = None) -> ExecutionResult
    def validate_security() -> dict
```

### ContextHandle

```python
class ContextHandle:
    size: int                    # File size in bytes
    size_mb: float              # File size in MB
    
    def search(pattern: str) -> List[Tuple[int, str]]
    def read_window(offset: int, radius: int = 500) -> str
    def snippet(offset: int, window: int = 500) -> str
    def head(n_bytes: int = 1000) -> str
    def tail(n_bytes: int = 1000) -> str
    def iterate_lines(start_line: int = 1) -> Iterator
```

### EgressFilter

```python
class EgressFilter:
    def filter(output: str, raise_on_leak: bool = False) -> str
    def check_entropy(text: str) -> Tuple[bool, float]
    def check_secrets(text: str) -> List[Tuple[str, str]]
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/ -v

# Run security tests (requires Docker)
pytest tests/security/ -v -m security

# With coverage
pytest --cov=rlm --cov-report=html
```

## 📁 Project Structure

```
src/rlm/
├── config/          # Pydantic Settings configuration
├── core/
│   ├── memory/      # ContextHandle for large files
│   ├── repl/        # Docker sandbox execution
│   ├── exceptions.py
│   └── orchestrator.py
├── llm/             # Multi-provider LLM clients
├── security/        # Egress filtering
├── utils/           # Cost management
└── prompt_templates/
```

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

Built following the security principles outlined in RFC-002 for hardened LLM code execution.
