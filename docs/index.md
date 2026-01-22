# RLM-Python

<div align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License">
  <img src="https://img.shields.io/pypi/v/rlm-python.svg" alt="PyPI Version">
</div>

<p align="center">
  <strong>Secure LLM-driven code execution with Docker sandboxing</strong>
</p>

---

**RLM-Python** (Recursive Language Model) is a Python library for safely executing LLM-generated code in isolated Docker containers. It provides enterprise-grade security through OS-level isolation, egress filtering, and memory-efficient context handling.

## ✨ Key Features

- 🐳 **Docker Sandbox Execution** - Execute untrusted code in isolated containers with gVisor support
- 🔐 **OS-Level Security** - Network isolation, memory limits, process limits, privilege restrictions
- 🛡️ **Egress Filtering** - Prevent data exfiltration via entropy detection and pattern matching
- 📚 **Memory-Efficient Context** - Handle gigabyte-scale files with mmap-based `ContextHandle`
- 🤖 **Multi-Provider LLM** - Support for OpenAI, Anthropic, and Google Gemini
- 💰 **Budget Management** - Track API costs and enforce spending limits

## 🚀 Quick Start

```bash
pip install rlm-python
```

```python
from rlm import Orchestrator

orchestrator = Orchestrator()
result = orchestrator.run("Calculate the first 10 prime numbers")
print(result.final_answer)
```

## 📖 Documentation

- [Installation Guide](getting-started/installation.md)
- [Quick Start Tutorial](getting-started/quickstart.md)
- [Configuration Reference](getting-started/configuration.md)
- [API Documentation](api/index.md)

## 🔒 Security

RLM v2.0 implements defense in depth with multiple security layers:

| Layer | Protection |
|-------|------------|
| **Runtime** | gVisor (runsc) kernel isolation |
| **Network** | Complete network isolation |
| **Resources** | Memory, CPU, PID limits |
| **Egress** | Entropy and pattern-based filtering |
| **Privileges** | No privilege escalation |

Learn more in the [Security Architecture](security/architecture.md) guide.
