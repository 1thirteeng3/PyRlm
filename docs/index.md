---
hide:
  - navigation
  - toc
---

<style>
.md-content__button {
  display: none;
}
.hero {
  text-align: center;
  padding: 4rem 0 2rem;
}
.hero h1 {
  font-size: 3rem;
  font-weight: 700;
  margin-bottom: 1rem;
}
.hero p {
  font-size: 1.25rem;
  opacity: 0.8;
  max-width: 600px;
  margin: 0 auto 2rem;
}
.hero-buttons {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}
.hero-buttons .md-button {
  padding: 0.75rem 2rem;
  font-size: 1rem;
}
.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
  padding: 3rem 0;
}
.feature {
  text-align: center;
  padding: 1.5rem;
}
.feature-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}
.feature h3 {
  margin-bottom: 0.5rem;
}
.demo-box {
  background: var(--md-code-bg-color);
  border-radius: 8px;
  padding: 1.5rem;
  margin: 2rem 0;
  font-family: var(--md-code-font-family);
  font-size: 0.85rem;
  overflow-x: auto;
}
</style>

<div class="hero">
  <h1>🛡️ RLM-Python</h1>
  <p>
    <strong>Secure Sandbox for AI Agents</strong><br>
    Replace unsafe <code>exec()</code> with Docker isolation, gVisor protection, and real-time data leak prevention.
  </p>
  <div class="hero-buttons">
    <a href="getting-started/quickstart/" class="md-button md-button--primary">
      Get Started
    </a>
    <a href="https://github.com/1thirteeng3/PyRlm" class="md-button">
      View on GitHub
    </a>
  </div>
</div>

---

## See It In Action

<div class="demo-box">
<pre>
┌─────────────────────────────────────────────────────────────────┐
│ $ python demo.py                                                │
│                                                                 │
│ 🤖 Agent: Attempting to read environment variables...           │
│ 📝 Code: import os; print(os.environ.get('API_KEY'))            │
│                                                                 │
│ 🛡️ <span style="color: #f44336;">[SECURITY REDACTION: Secret Pattern Detected]</span>                │
│    Egress filter blocked potential API key exfiltration.        │
│                                                                 │
│ 🤖 Agent: Let me calculate fibonacci instead...                 │
│ 📝 Code: def fib(n): return n if n < 2 else fib(n-1) + fib(n-2) │
│          print(f"FINAL({fib(10)})")                             │
│                                                                 │
│ <span style="color: #4caf50;">✅ Result: 55</span>                                                   │
└─────────────────────────────────────────────────────────────────┘
</pre>
</div>

---

## Why RLM-Python?

<div class="features">
  <div class="feature">
    <div class="feature-icon">🛡️</div>
    <h3>gVisor Security</h3>
    <p>Kernel-level syscall interception blocks dangerous operations before they reach your host.</p>
  </div>
  <div class="feature">
    <div class="feature-icon">⚡</div>
    <h3>AsyncIO Native</h3>
    <p>True non-blocking execution perfect for FastAPI, aiohttp, and concurrent workloads.</p>
  </div>
  <div class="feature">
    <div class="feature-icon">🔍</div>
    <h3>Egress Filtering</h3>
    <p>Shannon entropy detection catches API keys, JWTs, and secrets before they leave the sandbox.</p>
  </div>
  <div class="feature">
    <div class="feature-icon">📦</div>
    <h3>Clean Boot</h3>
    <p>Ephemeral containers with TemporaryDirectory cleanup. No state, no leaks, no traces.</p>
  </div>
</div>

---

## Quick Comparison

| Feature | `exec()` / `eval()` | LangChain REPL | **RLM v3.0** |
|---------|:-------------------:|:--------------:|:------------:|
| **Isolation** | ❌ None (Host) | ⚠️ Limited | ✅ Docker + gVisor |
| **Network** | 🔓 Open | 🔓 Open | 🔒 Blocked by Default |
| **Concurrency** | ❌ Blocking | ❌ Blocking | ✅ Native AsyncIO |
| **Data Leak Prevention** | ❌ None | ❌ None | ✅ Egress Filtering |
| **Resource Limits** | ❌ None | ❌ None | ✅ Memory/CPU/PIDs |

---

## Get Started in 60 Seconds

```python
import asyncio
from rlm import Orchestrator

async def main():
    agent = Orchestrator()
    result = await agent.arun("Calculate the first 10 prime numbers")
    print(result.final_answer)

asyncio.run(main())
```

[:material-rocket-launch: Quick Start Guide](getting-started/quickstart.md){ .md-button .md-button--primary }
[:material-shield-check: Security Architecture](security/architecture.md){ .md-button }
