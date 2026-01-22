<p align="center">
  <h1 align="center">🛡️ RLM-Python</h1>
  <p align="center">
    <strong>Secure Code Execution for AI Agents</strong>
  </p>
  <p align="center">
    Replace unsafe <code>exec()</code> with Docker sandboxes, gVisor isolation, and real-time data leak prevention.
  </p>
</p>

<p align="center">
  <a href="https://pypi.org/project/rlm-python/"><img src="https://img.shields.io/pypi/v/rlm-python?style=flat-square&color=blue" alt="PyPI Version"></a>
  <a href="https://pypi.org/project/rlm-python/"><img src="https://img.shields.io/pypi/pyversions/rlm-python?style=flat-square" alt="Python Versions"></a>
  <a href="https://github.com/1thirteeng3/PyRlm/actions"><img src="https://img.shields.io/github/actions/workflow/status/1thirteeng3/PyRlm/ci-quality.yml?style=flat-square&label=tests" alt="Build Status"></a>
  <a href="https://github.com/1thirteeng3/PyRlm/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License"></a>
  <a href="#security"><img src="https://img.shields.io/badge/security-gVisor%20enabled-success?style=flat-square" alt="gVisor"></a>
</p>

---

## 🎬 See It In Action

```
┌─────────────────────────────────────────────────────────────────┐
│ $ python demo.py                                                │
│                                                                 │
│ 🤖 Agent: Attempting to read environment variables...           │
│ 📝 Code: import os; print(os.environ.get('API_KEY'))            │
│                                                                 │
│ 🛡️ [SECURITY REDACTION: Secret Pattern Detected]                │
│    Egress filter blocked potential API key exfiltration.        │
│                                                                 │
│ 🤖 Agent: Let me calculate fibonacci instead...                 │
│ 📝 Code: def fib(n): return n if n < 2 else fib(n-1) + fib(n-2) │
│          print(f"FINAL({fib(10)})")                             │
│                                                                 │
│ ✅ Result: 55                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**RLM v3.0**: Blocking data exfiltration in real-time while enabling legitimate computation.

---

## 🎯 The Problem

Every AI agent framework has the same vulnerability: **unrestricted code execution**.

```python
# ❌ What most frameworks do (DANGEROUS!)
exec(llm_generated_code)  # Full access to your system

# ❌ Subprocess isn't better
subprocess.run(["python", "-c", code])  # Still on your host
```

**The risks:**
- 🔓 Access to environment variables (API keys, secrets)
- 📁 Read/write to your filesystem
- 🌐 Network requests to exfiltrate data
- 💣 Fork bombs, crypto miners, ransomware

---

## ✅ The Solution: RLM-Python

```python
# ✅ RLM: Secure by design
from rlm import Orchestrator

agent = Orchestrator()
result = await agent.arun("Analyze this data and find trends")

print(result.final_answer)  # Safe output, guaranteed
```

### Why RLM?

| Feature | `exec()` / `eval()` | LangChain REPL | **RLM v3.0** |
|---------|:-------------------:|:--------------:|:------------:|
| **Isolation** | ❌ None (Host) | ⚠️ Limited | ✅ Docker + gVisor |
| **Network** | 🔓 Open | 🔓 Open | 🔒 Blocked by Default |
| **Concurrency** | ❌ Blocking | ❌ Blocking | ✅ Native AsyncIO |
| **Data Leak Prevention** | ❌ None | ❌ None | ✅ Egress Filtering |
| **Binary Detection** | ❌ None | ❌ None | ✅ Fail-Fast |
| **Resource Limits** | ❌ None | ❌ None | ✅ Memory/CPU/PIDs |

---

## 🚀 Quick Start

### Installation

```bash
pip install rlm-python
```

### Prerequisites

> ⚠️ **Docker Engine is required.** RLM executes code in isolated containers.

```bash
# Verify Docker is running
docker --version
```

### Optional: Enable gVisor (Recommended for Production)

gVisor provides kernel-level syscall interception for maximum security.

```bash
# Install gVisor runtime
curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" | sudo tee /etc/apt/sources.list.d/gvisor.list > /dev/null
sudo apt-get update && sudo apt-get install -y runsc

# Configure Docker to use gVisor
sudo runsc install
sudo systemctl restart docker
```

---

## 💻 Usage Examples

### Modern Async/Await (Recommended)

```python
import asyncio
from rlm import Orchestrator

async def main():
    # Initialize the orchestrator (connects to Docker via aiodocker)
    agent = Orchestrator()
    
    # Execute non-blocking - perfect for web servers
    result = await agent.arun(
        "Calculate the first 20 prime numbers and return as a list"
    )
    
    print(f"Success: {result.success}")
    print(f"Answer: {result.final_answer}")
    print(f"Iterations: {result.iterations}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Synchronous (For Scripts)

```python
from rlm import Orchestrator

agent = Orchestrator()
result = agent.run("What is 2 + 2?")

print(result.final_answer)  # "4"
```

### With Large Context Files (Big Data)

```python
from rlm import Orchestrator

# Load a 1GB CSV - uses mmap for memory efficiency
# The LLM never reads the entire file, only snippets
result = agent.run(
    query="Find the top 10 customers by revenue",
    context_path="./sales_data_1gb.csv"
)
```

### FastAPI Integration

```python
from fastapi import FastAPI
from rlm import Orchestrator

app = FastAPI()
orchestrator = Orchestrator()

@app.post("/execute")
async def execute_code(query: str):
    # Non-blocking! Other requests proceed while this runs
    result = await orchestrator.arun(query)
    return {"answer": result.final_answer}
```

---

## 🔒 Security Architecture

RLM implements **Defense in Depth** with 5 security layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR APPLICATION                          │
├─────────────────────────────────────────────────────────────┤
│  L5: APPLICATION    │  Egress Filtering                     │
│                     │  • Shannon entropy detection          │
│                     │  • Secret pattern matching (API keys) │
│                     │  • Binary magic byte detection        │
├─────────────────────────────────────────────────────────────┤
│  L4: FILESYSTEM     │  Ephemeral Execution                  │
│                     │  • TemporaryDirectory (auto-cleanup)  │
│                     │  • Read-only volume mounts            │
│                     │  • No persistent state                │
├─────────────────────────────────────────────────────────────┤
│  L3: NETWORK        │  Air-Gapped by Default                │
│                     │  • network_mode="none"                │
│                     │  • Zero outbound connections          │
├─────────────────────────────────────────────────────────────┤
│  L2: KERNEL         │  Syscall Interception (gVisor)        │
│                     │  • Blocks dangerous syscalls          │
│                     │  • Sandboxed kernel interface         │
├─────────────────────────────────────────────────────────────┤
│  L1: CONTAINER      │  Namespace Isolation (Docker)         │
│                     │  • Memory limits (default: 256MB)     │
│                     │  • CPU limits (default: 0.5 cores)    │
│                     │  • PID limits (default: 50)           │
│                     │  • no-new-privileges                  │
└─────────────────────────────────────────────────────────────┘
```

### Fail-Closed Policy

RLM **refuses to execute** if gVisor is not detected:

```python
# This will FAIL if gVisor is not installed
agent = Orchestrator()
result = agent.run("print('hello')")  # SecurityViolationError!

# Explicit opt-in for reduced security (NOT RECOMMENDED)
from rlm.core.repl import SandboxConfig
config = SandboxConfig(allow_unsafe_runtime=True)
```

This is **intentional**. We believe security should be the default, not an option.

---

## ⚙️ Configuration

Environment variables for customization:

```bash
# Docker
RLM_DOCKER_IMAGE=python:3.11-slim
RLM_DOCKER_RUNTIME=auto  # auto | runsc | runc

# Limits
RLM_MEMORY_LIMIT=256m
RLM_CPU_LIMIT=0.5
RLM_PIDS_LIMIT=50
RLM_EXECUTION_TIMEOUT=30

# Security
RLM_ALLOW_UNSAFE_RUNTIME=0  # Set to 1 to allow without gVisor
RLM_NETWORK_ENABLED=0       # Set to 1 to enable network (risky!)

# Egress
RLM_ENTROPY_THRESHOLD=4.5   # Shannon entropy for secret detection
RLM_MAX_STDOUT_BYTES=4000   # Truncate large outputs

# LLM
RLM_LLM_PROVIDER=openai
RLM_LLM_MODEL=gpt-4
OPENAI_API_KEY=sk-...
```

---

## 📖 Documentation

**[📚 Read the Full Documentation](https://rlm-python.readthedocs.io)**

- [Configuration Reference](https://rlm-python.readthedocs.io/configuration)
- [Custom Docker Images](https://rlm-python.readthedocs.io/custom-images)
- [LangChain Integration](https://rlm-python.readthedocs.io/integrations/langchain)
- [FastAPI Best Practices](https://rlm-python.readthedocs.io/integrations/fastapi)

---

## 🗺️ Roadmap

**v3.0** - Stable Release ✅

- [x] DRY Architecture (Single Source of Truth)
- [x] Strict mistletoe parsing (no regex fallback)
- [x] TemporaryDirectory for crash-safe cleanup
- [x] CPU offloading via ThreadPoolExecutor
- [x] Binary file detection in ContextHandle

**Future**

- [ ] Kubernetes support (K8s Jobs)
- [ ] Official CrewAI integration
- [ ] WebAssembly runtime option
- [ ] Multi-language support (JavaScript, Rust)

---

## 🤝 Contributing

We welcome contributions, especially security improvements!

```bash
# Clone and setup
git clone https://github.com/1thirteeng3/PyRlm.git
cd PyRlm
pip install -e ".[dev]"

# Run tests
pytest tests/unit/ -v

# Run security tests (requires Docker + gVisor)
pytest tests/integration/ -v -m security
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Built with 🛡️ for the AI Agent community</strong>
  <br>
  <a href="https://github.com/1thirteeng3/PyRlm">GitHub</a> •
  <a href="https://pypi.org/project/rlm-python/">PyPI</a> •
  <a href="https://rlm-python.readthedocs.io">Docs</a>
</p>
