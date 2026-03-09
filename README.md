# PyRlm — Reinforcement Learning Models for Cognitive and Agent Architectures

[![PyPI](https://img.shields.io/pypi/v/pyrlm.svg)](https://pypi.org/project/pyrlm/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/pyrlm.svg)](https://pypi.org/project/pyrlm/)
[![Python Version](https://img.shields.io/pypi/pyversions/pyrlm.svg)](https://pypi.org/project/pyrlm/)
[![License](https://img.shields.io/pypi/l/pyrlm.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-experimental-orange)](#project-status)
[![CI](https://img.shields.io/github/actions/workflow/status/1thirteeng3/PyRlm/ci-quality.yml?branch=main&style=flat-square&label=tests)](https://github.com/1thirteeng3/PyRlm/actions/workflows/ci-quality.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18568094.svg)](https://doi.org/10.5281/zenodo.18568094)


PyRlm is an **experimental Python library for Reinforcement Learning Models (RLMs)** focused on exploring learning, decision-making, and control beyond classical Deep Reinforcement Learning pipelines.

Instead of centering exclusively on optimization algorithms, PyRlm treats Reinforcement Learning as a **modeling paradigm** — enabling experimentation with:
- cognitive and symbolic abstractions,
- agent orchestration,
- controlled and secure execution,
- hybrid decision systems.

PyRlm is designed for **research, prototyping, and conceptual exploration**, not as a drop-in replacement for mainstream RL frameworks.

---

## Installation

```bash
pip install pyrlm
```

## Why PyRlm?

Most Reinforcement Learning libraries focus on:
- algorithmic benchmarks,
- gradient-based optimization,
- environment–policy loops tightly coupled to simulators.

PyRlm explores a different axis.

It asks questions such as:
- What is a Reinforcement Learning Model independent of a specific algorithm?
- How can agents reason, decide, and act under reinforcement-like dynamics while remaining inspectable?
- How can learning-driven agents be safely executed, orchestrated, and constrained?

PyRlm is built to support conceptual, architectural, and experimental work at the intersection of:
- Reinforcement Learning
- Cognitive architectures
- Agent systems
- Symbolic and hybrid AI
- Secure agent execution

## Core Concepts

PyRlm is organized around a small set of architectural ideas rather than a large collection of algorithms.

### Reinforcement Learning Models (RLM)

In PyRlm, an RLM is treated as a structural model of interaction, not merely an optimizer.
An RLM may include:
- reward signals,
- decision policies,
- memory or state abstractions,
- constraints and safety boundaries,
- execution rules.

This makes PyRlm suitable for non-standard RL formulations.

### Agents and Orchestration

PyRlm supports the construction of agents that:
- reason over tasks,
- execute actions programmatically,
- interact with environments or instructions,
- operate under explicit control flows.

Agent orchestration is treated as a first-class concern, not an afterthought.

### Secure and Controlled Execution

Executing agent-generated code or actions is inherently risky.

PyRlm includes mechanisms for controlled execution environments, allowing agents to:
- run code in isolated contexts,
- respect execution boundaries,
- reduce unintended side effects.

This is particularly relevant for AI agents interacting with real systems.

## Quick Example

```python
from pyrlm import Orchestrator

agent = Orchestrator()

result = agent.run(
    task="Solve the task using a reinforcement-based reasoning process",
    constraints={
        "time_limit": 5,
        "safe_execution": True
    }
)

print(result)
```

> **Note:** PyRlm prioritizes clarity and inspectability over raw performance.

## What PyRlm Is Not

To avoid confusion, PyRlm is not:
- a high-performance Deep RL training framework,
- a benchmark-oriented RL library,
- a replacement for tools like TorchRL, Stable-Baselines, or RLlib.

Instead, it complements them by focusing on modeling, structure, and experimentation.

## Use Cases

PyRlm is well-suited for:
- experimental Reinforcement Learning research,
- cognitive and symbolic agent modeling,
- AI agent orchestration and control,
- safety-aware agent execution,
- prototyping hybrid learning systems,
- philosophical and theoretical exploration of RL concepts.

## Project Status

PyRlm is currently in early-stage development.

Expect:
- rapid iteration,
- evolving APIs,
- conceptual shifts as research progresses.

Stability is secondary to exploration and learning at this stage.

## Roadmap (Indicative)

- Expand core RLM abstractions
- Improve agent orchestration interfaces
- Add example notebooks and experiments
- Formalize execution safety layers
- Explore symbolic and hybrid learning models
- Improve documentation and theoretical grounding

## Contributing

Contributions are welcome, especially in:
- experimental models,
- architectural discussions,
- documentation and examples,
- safety and execution mechanisms.

If you are interested in Reinforcement Learning beyond standard formulations, PyRlm is an open playground.

## Citation

If you use PyRlm in academic work, please cite it using the provided `CITATION.cff` file or via its Zenodo DOI.

## License

MIT License

## Author

Developed and maintained by Giovanni Lemos Barcelos.

This project is part of a broader exploration of Reinforcement Learning, cognitive systems, and experimental AI architectures.
