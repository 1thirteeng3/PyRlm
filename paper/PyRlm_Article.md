# PyRlm: Reinforcement Learning Models as Architectural Constructs for Agent Systems

**Giovanni Lemos Barcelos**  
*Independent Researcher*  
*February 2026*

**Abstract**  
While current Reinforcement Learning (RL) libraries focus predominantly on algorithmic optimization and benchmark performance, the field lacks dedicated abstractions for treating RL models as inspectable architectural constructs within hybrid agent systems. This work introduces **PyRlm**, an experimental Python library that formalizes "Reinforcement Learning Models" (RLMs) not as mere optimizers, but as structural components encapsulating state abstraction, decision logic, and execution constraints. PyRlm contributes: (i) a rigorous definition of RLMs as explicit architectural tuples; (ii) a secure, containerized execution environment for agentic code; (iii) a first-class orchestration layer for hybrid decision-making; and (iv) deep inspectability mechanisms for tracing agent reasoning. We demonstrate through architectural analysis and case studies that PyRlm enables the construction of safe, reproducible, and verifiable agent systems, offering a robust foundation for research into cognitive architectures and safe AI execution.

**Keywords:** Reinforcement Learning, agent orchestration, cognitive architectures, symbolic AI, hybrid AI, inspectability, safe execution, research software, decision-making models, controlled environments.

---

## 1. Introduction

### 1.1 Motivation and Context
Reinforcement Learning (RL) has matured from a theoretical curiosity to a powerful paradigm for solving decision-making problems. However, in practice, the term "Reinforcement Learning" often conflates two distinct things: the *learning algorithm* (e.g., PPO, DQN) and the *interaction model* (the agent-environment loop). Mainstream libraries like Stable-Baselines3, RLlib, and TorchRL excel at the former—providing optimized implementations of gradient-based algorithms to maximize reward on standardized benchmarks. 

However, as the field moves toward **autonomous agents** and **cognitive architectures**, the limitations of algorithm-centric libraries become apparent. Researchers building Large Language Model (LLM) agents, symbolic hybrids, or safety-critical systems often find themselves re-implementing the "interaction scaffolding"—state management, memory, action execution, and safety constraints—from scratch, often in ad-hoc ways.

### 1.2 Problem Statement
There is a lack of "model-level abstractions" for RL. Current frameworks treat the *agent* largely as a neural network policy to be optimized, rather than a structured system that reasons, acts, and adheres to constraints. This gap leads to opaque agent behaviors, difficulty in enforcing safety boundaries (e.g., preventing dangerous code execution), and a lack of inspectability into *why* a specific decision chain occurred.

### 1.3 Contributions: PyRlm
PyRlm explores a different axis. It formalizes the concept of a **Reinforcement Learning Model (RLM)** as a distinct architectural entity. PyRlm offers:

1.  **Operational Definition of RLM**: A formal separation of the interaction model (state, action, constraints) from the optimization strategy.
2.  **Secure Execution Environment**: A rigorous `DockerSandbox` with gVisor integration, enforcing fail-closed security for agents that generate and execute code.
3.  **Orchestration Layer**: A "Single Source of Truth" `Orchestrator` that manages the cyclic flow of observation, reasoning, action, and feedback.
4.  **Deep Inspectability**: Built-in instrumentation that traces every `ExecutionStep`, encompassing inputs, outputs, resource usage, and security events.
5.  **Hybrid Capability**: First-class support for combining symbolic reasoning, LLM-based planning, and traditional control flow.

### 1.4 Scope and Roadmap
PyRlm is designed for **research, prototyping, and conceptual exploration**, not as a high-throughput training framework for deep RL. It does not replace libraries like TorchRL but complements them by providing the structural "host" for complex agents.

The remainder of this paper is organized as follows: Section 2 reviews related work. Section 3 defines the RLM concept. Section 4 details the PyRlm system architecture. Section 5 presents the API. Section 6 discusses instrumentation and safety. Section 7 provides a qualitative evaluation. Section 8 discusses limitations, and Section 9 concludes.

---

## 2. Background & Related Work

### 2.1 Reinforcement Learning (RL)
Classical Reinforcement Learning formalizes decision-making as an agent–environment interaction optimized via reward maximization, most commonly expressed through Markov Decision Processes (MDPs) [Sutton & Barto, 2018]. Modern RL frameworks extend this formulation with deep function approximators and scalable training pipelines, prioritizing algorithmic performance and benchmark-driven evaluation [Li, 2017; Liang et al., 2018].

While these approaches have achieved remarkable success in control and game-playing domains, they typically treat execution, safety constraints, and agent reasoning structures as external concerns. The interaction model itself is often implicit, embedded within training loops rather than represented as an explicit, inspectable architectural object.

PyRlm operates orthogonally to this paradigm by treating the Reinforcement Learning Model as a first-class architectural construct, decoupling interaction structure from optimization strategy.

### 2.2 Agent Systems & Orchestration
Recent agent frameworks have popularized the notion of autonomous systems capable of reasoning, tool use, and multi-step task execution, particularly in the context of large language models [Xi et al., 2023; Wu et al., 2023]. These systems emphasize orchestration and practical usability, often relying on prompt engineering and informal control flow to guide agent behavior. Tool-using agent paradigms such as ReAct-style reasoning-action loops highlight the need for explicit action semantics and step-level traceability in agent systems [Yao et al., 2022].

However, many agent frameworks lack explicit definitions of state transitions, constraints, and execution boundaries, making it difficult to reason formally about agent behavior or enforce safety guarantees. Cognitive architectures have long explored structured agent models [Laird et al., 1987], but often without integration into modern AI tooling.

PyRlm bridges this gap by grounding agent orchestration in Reinforcement Learning formalisms, making state, action, and constraint handling explicit and inspectable.

### 2.3 Safety, Execution & Inspectability
As AI systems increasingly execute code and interact with real-world resources, execution safety and observability have become central concerns [Amodei et al., 2016]. Practical isolation mechanisms for untrusted workloads have been studied extensively in systems security, and modern sandboxing approaches such as gVisor provide syscall-interposition and container hardening that strengthens isolation beyond standard namespace-based containerization [gVisor Team, 2018].

In parallel, research on AI interpretability and system auditing emphasizes the importance of traceability and accountability in autonomous decision-making. Despite this, many RL and agent frameworks treat execution environments and instrumentation as external infrastructure layers.

PyRlm integrates execution constraints and instrumentation directly into the Reinforcement Learning Model, treating safety and inspectability as intrinsic components rather than optional add-ons.

---

## 3. Reinforcement Learning Models (RLM): Definition & Scope

In PyRlm, we define a Reinforcement Learning Model not as a neural network, but as a tuple representing the structural components of an autonomous system.

**Definition 1 (RLM Tuple).** An RLM is defined as a tuple $\mathcal{M} = \langle \tilde{S}, A, T, R, \pi, C, I, E \rangle$, where:

*   **$\tilde{S}$ (State Abstraction):** The internal representation of the environment, which may be symbolic, latent, or structured data (managed via `ContextHandle`).
*   **$A$ (Action Space):** The set of valid operations, including tool calls, code execution, or communicative acts.
*   **$T$ (Transition Model):** The mechanism updating $\tilde{S}$ based on actions (often implicit in model-free settings, but explicit in PyRlm's orchestration).
*   **$R$ (Reward/Utility):** Scaling feedback signals driving the agent's objectives.
*   **$\pi$ (Policy):** The decision rule mapping $\tilde{S} \to A$. In PyRlm, this can be an LLM, a heuristic, or a hybrid system.
*   **$C$ (Constraints):** Hard boundaries on behavior (e.g., resource limits, safety filters) that override $\pi$.
*   **$I$ (Instrumentation):** The observation layer responsible for logging traces, metrics, and intermediate reasoning artifacts.
*   **$E$ (Execution Model):** The specific runtime where $a \in A$ is realized (e.g., a sandboxed container).


This formalization allows researchers to isolate and experiment with specific components (e.g., changing $E$ from local to sandboxed, or swapping $\pi$ from GPT-4 to a symbolic planner) without rewriting the entire agent.

### 3.1 Formal Relationship to MDPs and Extensions

Reinforcement Learning is most commonly formalized through Markov Decision Processes (MDPs), which provide a mathematically clean representation of sequential decision-making under uncertainty. However, many practical agent systems—particularly tool-using, hybrid, or safety-critical agents—embed additional assumptions and mechanisms that remain implicit in the MDP formalism (e.g., execution semantics, constraints, and observability infrastructure). In this section, we situate the proposed Reinforcement Learning Model (RLM) abstraction within the classical RL formalism and its standard extensions, and we delineate the precise ways in which PyRlm intentionally generalizes and diverges from these formulations.

#### 3.1.1 Relationship to Markov Decision Processes (MDPs)

A classical MDP is defined as a tuple $\mathcal{M}_{MDP} = \langle S, A, P, R, \gamma \rangle$, where $S$ is the set of environment states, $A$ is the set of actions, $P(\cdot \mid s, a)$ is the transition kernel, $R(s, a, s') \in \mathbb{R}$ is the reward function, and $\gamma \in [0, 1)$ is a discount factor. The central object in most RL libraries is a policy $\pi(a \mid s)$ (often parameterized by a neural network) optimized to maximize expected discounted return.

In contrast, PyRlm defines a Reinforcement Learning Model (RLM) as a tuple $\mathcal{M}_{RLM} = \langle \tilde{S}, A, T, R, \pi, C, I, E \rangle$, where $\tilde{S}$ denotes an internal state abstraction space (not necessarily identical to the environment state space), $T$ is a transition mechanism over $\tilde{S}$, $C$ is a constraint layer, $I$ is an instrumentation layer, and $E$ is an execution model specifying the runtime semantics of actions.

This construction can be viewed as a structural generalization of the MDP framework. The correspondence between core elements is as follows:

**State**: Classical MDPs model decision-making over $S$. RLMs model decision-making over an internal abstraction $\tilde{S}$, which may be symbolic, latent, structured memory, document-derived, or otherwise engineered. Importantly, $\tilde{S}$ is not required to satisfy Markovian sufficiency; it is an explicit design choice.

**Actions**: Both formalisms include an action space $A$. In RLMs, $A$ may include temporally extended or structured actions (tool calls, code execution, I/O operations), rather than atomic control moves only.

**Transitions**: In MDPs, transitions are represented by a kernel $P(s' \mid s, a)$. In RLMs, transitions occur over $\tilde{S}$ via a mechanism $T$ which may be deterministic or stochastic:
$T: \tilde{S} \times A \to \tilde{S} \quad \text{or} \quad T: \tilde{S} \times A \to P(\tilde{S})$.
The key difference is that $T$ is permitted to encode architectural update rules (e.g., memory updates, context indexing, document retrieval) that are typically externalized in algorithm-centric RL tooling.

**Rewards/Utility**: Both frameworks include a feedback signal. RLMs adopt the standard functional form $R: \tilde{S} \times A \times \tilde{S} \to \mathbb{R}$, while allowing for structured or vector-valued utility in research settings when appropriate.

**Policy**: Classical RL generally assumes a policy $\pi(a \mid s)$. RLMs define the policy as a mapping from internal abstractions to action distributions: $\pi: \tilde{S} \to P(A)$, with deterministic policies as the special case $\pi: \tilde{S} \to A$.

Crucially, standard MDP-based approaches typically treat constraints, instrumentation, and execution semantics as implementation details or environment assumptions. RLMs make these aspects explicit components of the model:
*   $C$ formalizes constraints as a first-class boundary over action admissibility.
*   $I$ formalizes structured observability of decision processes.
*   $E$ formalizes runtime semantics of action realization (including isolation, failure modes, and resource boundaries).

This perspective does not reject MDPs; rather, it treats the MDP as an inner core embedded within a broader system-level model. In particular, if one chooses $\tilde{S} = S$, sets $C$ to the trivial predicate that always returns true, $I$ to a null observer, and $E$ to an identity execution mapping, then the RLM reduces conceptually toward a classical MDP setting.

#### 3.1.2 Compatibility with POMDP and Semi-MDP Extensions

**Partial Observability and POMDP Alignment**

A Partially Observable MDP (POMDP) is commonly defined as $\mathcal{M}_{POMDP} = \langle S, A, P, R, \Omega, O, \gamma \rangle$, where $\Omega$ is an observation space and $O(o \mid s)$ is an observation model. Agents do not directly observe $s \in S$, but instead receive observations $o \in \Omega$, often maintaining a belief state $b(s)$ as a sufficient statistic.

RLMs align naturally with partial observability through the explicit distinction between environmental reality and internal abstraction: the internal abstraction $\tilde{S}$ need not be the environment state $S$, and is explicitly allowed to be a function of observation history, memory, retrieval, or symbolic processing. In this view, $\tilde{S}$ can be understood as an architectural analogue of a belief state or information state, but without requiring a probabilistic belief update or a particular Bayesian semantics. That is, while POMDPs frequently emphasize belief state filtering and optimality under partial observability, RLMs treat state abstraction as a design degree of freedom that can represent belief-like constructs, symbolic summaries, retrieved context, or structured memory.

Formally, this permits an interpretation where $\tilde{S}$ is generated by an abstraction mechanism $f$ acting on observation history:
$\tilde{s}_t = f(o_{0:t}, a_{0:t-1})$, with $f$ potentially implemented by symbolic pipelines, retrieval systems, learned encoders, or hybrid combinations. In PyRlm, the system-level transition mechanism $T$ may incorporate both environmental feedback and internal memory evolution, providing a practical and inspectable locus for reasoning about partial observability at the architectural level.

**Temporally Extended Actions and Semi-MDP / Options Alignment**

Many agent actions in contemporary systems are not instantaneous. Tool calls, code execution, file processing, and multi-step interactions may have variable durations and may internally involve multiple sub-steps. Classical MDPs assume discrete-time transitions per action. Semi-Markov Decision Processes (Semi-MDPs) extend MDPs by allowing actions with variable duration, typically capturing the idea that an action may take $k$ time units and accumulate reward over a temporal segment.

RLMs are compatible with Semi-MDP and options-based formulations because the action space $A$ is explicitly permitted to include temporally extended actions. In such cases, the execution model $E$ provides semantics for action realization, including duration, failure modes, and resource use, while instrumentation $I$ can record execution-level traces. Conceptually, one may interpret an action $a \in A$ as an option-like macro-action with implicit termination determined by the execution runtime:
1.  The system triggers $a$.
2.  Execution produces an observable outcome $o$.
3.  The internal state abstraction updates accordingly via $T$.

PyRlm does not require a fully explicit option-termination function $\beta$ or a duration model $\tau$ to be specified in closed form; instead, temporal structure is handled at the orchestration and execution layers, which is a deliberate design choice for research systems where actions correspond to tool invocations rather than pure control primitives.

#### 3.1.3 Intentional Divergences in PyRlm

While RLMs are compatible with classical RL formalisms, PyRlm intentionally diverges in three principal ways that reflect the realities of hybrid agent systems.

**(1) Execution Semantics as a Model Component**

Classical RL abstractions largely treat action execution as instantaneous and abstract. In practice, especially for tool-using agents, action execution occurs within a concrete runtime that introduces additional semantics: sandboxing, permissions, I/O policies, timeouts, resource constraints, and failure modes. These execution semantics are central to safety and correctness, yet they are often externalized as “engineering details.”

PyRlm makes execution explicit via the execution model $E$. At a minimal level, $E$ can be treated as a mapping from actions to observable outcomes: $E: A \to O$, where $O$ is a space of execution outcomes (including stdout/stderr, structured outputs, error states, and execution metadata). More generally, $E$ may be viewed as defining the operational semantics of action realization under a controlled runtime. This enables system-level reasoning about failure modes and enforcement boundaries as part of the formal model, rather than as assumptions hidden outside the RL formulation.

**(2) Constraints as Hard Boundaries (Not Reward Shaping)**

In standard RL, constraints are often encoded indirectly via reward shaping, environment design, or post-hoc filtering. These approaches can be insufficient in safety-critical settings: a policy may still propose unsafe actions if they appear reward-maximizing under the learned model.

PyRlm introduces an explicit constraint layer $C$ as a hard boundary over admissible actions. Formally, constraints may be represented as a predicate $C: \tilde{S} \times A \to \{0, 1\}$, or equivalently as an action filter/transformer $C: \tilde{S} \times A \to A \cup \{\emptyset\}$, where $\emptyset$ denotes rejection. This formalization supports the design principle that constraints may override policy output irrespective of the policy’s preferences. In other words, $C$ is not a learned preference; it is a governance layer.

**(3) Instrumentation as a First-Class Formal Element**

Inspectability is often treated as a logging concern external to the model. However, in research and safety contexts, the ability to trace why an agent acted in a certain way—what it saw, what it decided, what it executed, and what outcomes occurred—is not optional.

PyRlm therefore introduces instrumentation $I$ as an explicit element of the RLM tuple. A minimal formalization treats instrumentation as a mapping to a structured observation/trace space $O$: $I: (\tilde{S}, A, \tilde{S}) \to O$, where $O$ may encode event logs, step-level metadata, resource usage, and constraint-trigger events. Importantly, $I$ is defined as observational, not dynamical: it does not change the underlying transition semantics directly, but makes the system’s evolution systematically measurable and replayable. This shifts inspectability from an implementation detail to a formal design objective.

#### 3.1.4 Summary: RLMs as an Architectural Layer Over Classical RL

RLMs should not be interpreted as a replacement for MDPs or their extensions. Rather, they define an architectural layer that makes explicit several assumptions often left implicit in reinforcement learning systems—particularly those concerning action execution, constraints, and observability. By explicitly representing these elements in the model tuple, PyRlm provides a framework for designing and analyzing hybrid agent systems that are inspectable by default and amenable to controlled execution.

This perspective is especially relevant for modern agent architectures where actions correspond to tool invocations and code execution, where state is an engineered abstraction over long context and memory, and where safety boundaries must be enforced as hard constraints rather than as emergent properties of reward maximization.

---

## 4. System Overview: PyRlm Architecture

PyRlm operationalizes the RLM definition through a modular architecture designed for **inspectability by default**.

### 4.1 Architectural Components
1.  **Orchestrator**: The central "brain" acting as the transition engine ($T$). It implements the cyclic loop of `Observe -> Reason -> Act -> Feedback`. It serves as the Single Source of Truth for the agent's lifecycle.
2.  **ContextHandle**: Manages the State Abstraction ($\tilde{S}$), providing a unified interface for agents to read, write, and search structured memory or documents.
3.  **DockerSandbox**: The reification of the Execution Model ($E$). It provides a secure, isolated runtime for executing code-based actions ($A$).
4.  **EgressFilter**: Implements Constraints ($C$) related to data safety, preventing secret exfiltration or dangerous binary outputs.

### 4.2 Data & Control Flow
The flow is strictly sequential and traceable:
1.  **Input**: User query + Context ($\tilde{S}_0$).
2.  **Reasoning**: `Orchestrator` consults Policy ($\pi$) (e.g., LLM) to generate an Action ($a_t$).
3.  **Constraint Check**: Action $a_t$ is validated against immutable Constraints ($C$).
4.  **Execution**: Valid actions are sent to `DockerSandbox` ($E$).
5.  **Feedback**: Result $o_t$ is filtered by `EgressFilter` and returned as the next observation.
6.  **Update**: $\tilde{S}_{t+1}$ is updated, and the cycle repeats.

---

## 5. API & Usage Patterns

PyRlm provides a clean, pythonic API that mirrors the architectural concepts.

### 5.1 Quickstart (Synchronous)
For simple use cases, the `Orchestrator` handles the complexity, providing a `run()` method that initializes the sandbox and manages the loop.

```python
from pyrlm import Orchestrator

# Initialize the agent (implicitly sets up Docker sandbox)
agent = Orchestrator()

# Run a task
result = agent.run("Calculate the 10th Fibonacci number")

print(f"Answer: {result.final_answer}")
print(f"Iterations: {result.iterations}")
```

### 5.2 Advanced: Async & Constraints
For high-performance or web-based applications, `arun()` provides non-blocking execution with custom constraints.

```python
import asyncio
from pyrlm import Orchestrator, OrchestratorConfig

async def main():
    config = OrchestratorConfig(
        max_iterations=5,
        raise_on_leak=True  # Strict security constraint
    )
    agent = Orchestrator(config=config)
    
    # Non-blocking call
    result = await agent.arun(
        "Analyze this text for patterns",
        context_path="./data.txt"
    )
    
    if result.success:
        print("Analysis complete:", result.final_answer)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 6. Instrumentation & Tracing

### 6.1 Observability as a First-Class Model Component

In PyRlm, instrumentation is treated as a first-class component of the Reinforcement Learning Model rather than as an auxiliary debugging mechanism. Classical RL systems typically expose only aggregated metrics (e.g., reward curves or loss values), which obscure the causal chain leading to individual decisions.

By explicitly modeling instrumentation as $I$ in the RLM tuple, PyRlm defines the design contract that every state transition, action execution, and constraint intervention should be observable, serializable, and replayable.

**Invariant 1 (Observability):** For every transition $\tilde{S}_t \to \tilde{S}_{t+1}$, there exists a corresponding trace event $e_t \in I$ capturing the decision, execution context, and outcome.

### 6.2 Event Schema Definition

We define the observable alphabet of the system through a rigorous event model.

#### 6.2.1 Event Model (Formal)

**Definition 2 (Trace Event).** A trace event is defined as a tuple
$$ e = \langle id, t, k, s, a, o, c, m \rangle $$
where:

| Field | Type | Description |
| :--- | :--- | :--- |
| **id** | UUID | Unique identifier for the event. |
| **t** | int | Logical step / iteration index. |
| **k** | Enum | Event kind (type). |
| **s** | hash | Hash of the abstract state $\tilde{S}$ before action. |
| **a** | object | The proposed or executed action. |
| **o** | object | Observable result (stdout, stderr, tool output). |
| **c** | list | List of active constraints triggered or enforced. |
| **m** | dict | Metadata (timestamps, resource usage, token counts). |

**Implementation Mapping**: In the current implementation, the abstract event fields map to the serialized trace schema as follows: $id \to$ `event_id`, $t \to$ `step`, $k \to$ `event_type`, $s \to$ `state_hash`, $a \to$ `action`, $o \to$ `output`, $c \to$ `constraints`, and $m \to$ `metrics` + `timestamp`. This mapping preserves the formal structure while allowing the serialization schema to evolve.

#### 6.2.2 Event Types

The set of event types $K$ is finite and explicit:

```text
EventType ::= 
    OBSERVATION_RECEIVED    | POLICY_INVOKED
  | ACTION_PROPOSED         | CONSTRAINT_TRIGGERED
  | ACTION_EXECUTED         | EXECUTION_FAILED
  | REWARD_OBSERVED         | STATE_UPDATED
```

Semantically, each event type guarantees specific system properties. For example, `CONSTRAINT_TRIGGERED` events are emitted whenever a hard constraint overrides or blocks an action, ensuring that safety interventions are explicitly observable rather than silent.

#### 6.2.3 Formal Invariants

The event stream must satisfy the following causal invariants:
1.  `ACTION_EXECUTED` $\implies$ must follow `ACTION_PROPOSED`.
2.  `STATE_UPDATED` $\implies$ must follow `ACTION_EXECUTED` $\lor$ `EXECUTION_FAILED`.
3.  `CONSTRAINT_TRIGGERED` $\implies$ must precede or replace execution.

### 6.3 Trace Serialization Format

Traces are designed to be persistent, runtime-independent, and offline-analyzable.

#### 6.3.1 Canonical Format

PyRlm serializes traces as **append-only JSON Lines (JSONL)** files, where each line corresponds to a single trace event $e_t$. This format supports streaming writes (vital for long-running agents), efficient diffing, and compatibility with standard data processing tools.

#### 6.3.2 Concrete Trace Example

```json
{
  "event_id": "b7e1f0a9-4d6a-4a2b-9876-123456789abc",
  "step": 2,
  "event_type": "ACTION_EXECUTED",
  "state_hash": "3fa85f64...",
  "action": {
    "type": "python_execution",
    "code": "print(fib(10))"
  },
  "output": {
    "stdout": "55\\n",
    "stderr": ""
  },
  "constraints": [],
  "metrics": {
    "cpu_ms": 12,
    "memory_mb": 32,
    "tokens": 184
  },
  "timestamp": "2026-02-09T14:33:21Z"
}
```

This structure allows researchers to analyze execution costs (`cpu_ms`), verify correctness (`stdout`), and audit inputs (`code`) for any specific step without re-running the agent.

#### 6.3.3 Trace Completeness Contract

**Invariant 2 (Trace Completeness):** Scope of “external effect.” In this paper, an external effect denotes any stateful interaction that crosses the orchestration boundary, i.e., any effect realized through an explicit action interface (tool call, code execution, file I/O within the sandbox, or emitted outputs). Effects that bypass the orchestrated action interface (e.g., side channels, non-instrumented subprocesses, or platform-level behaviors outside the sandbox) are out of scope for the completeness contract and are treated as limitations of the execution environment rather than of the trace schema.

### 6.4 Deterministic Replay and Debugging

PyRlm leverages this formal structure to transform debugging from ad-hoc logging into a scientific process.

#### 6.4.1 Replay Model

We define replay as a deterministic function:
$$ Replay(\mathcal{T}, \tilde{S}_0) \to \langle \tilde{S}_1, \dots, \tilde{S}_n \rangle $$
Where $\mathcal{T}$ is the ordered set of recorded events and $\tilde{S}_0$ is the initial state. Crucially, replay bypasses the stochastic policy $\pi$ and instead forces the transition mechanism $T$ to utilize the recorded actions $a \in \mathcal{T}$ and outcomes $o \in \mathcal{T}$.

#### 6.4.2 Causal Debugging

By decoupling decision generation from execution during replay, PyRlm allows researchers to isolate whether failures originate from:
*   **Policy Reasoning**: The model chose the wrong action given the state.
*   **Environmental Execution**: The code failed or the environment behaved unexpectedly.
*   **Constraint Enforcement**: A safety check incorrectly blocked a valid action.

#### 6.4.3 Debugging Workflows

This enables a clear research workflow:
1.  **Run experiment** $\to$ generates Trace $\mathcal{T}$.
2.  **Detect failure** at step $t$.
3.  **Replay** with variations:
    *   *Different Policy*: Keep state, swap $\pi$.
    *   *Same Actions*: Verify determinism of $E$.
    *   *Altered Constraints*: Test if relaxed safety solves the failure.

This connects the theoretical RLM definition to the practical reality of engineering reliable agent systems.

---

## 7. Controlled Execution Model

Executing agent-generated code is inherently risky. PyRlm implements a defense-in-depth strategy defining the Execution Model ($E$).

### 7.1 Threat Model
We assume the agent ($A$) is powerful but unreliable or potentially compromised (e.g., prompt injection). The goal is to prevent:
1.  **Host Compromise**: Filesystem access, env var theft.
2.  **Resource Exhaustion**: Fork bombs, OOM attacks.
3.  **Data Exfiltration**: Sending secrets to external servers.

### 7.2 The Hardware: Docker + gVisor
PyRlm employs `DockerSandbox` with **gVisor (`runsc`)** as the runtime. gVisor intercepts syscalls in userspace, providing a strong isolation boundary distinct from standard container namespaces.
*   **Network**: `network_mode="none"` (air-gapped).
*   **Filesystem**: Read-only mounts for context and libraries.
*   **Resources**: Hard CPU and Memory quotas.

Out of scope and non-goals. PyRlm’s controlled execution model is designed to reduce risk for agent-generated code under a practical threat model. It does not claim to provide formal security proofs, nor does it address the full spectrum of systems-security threats. In particular, the following are out of scope for the current work: (i) side-channel attacks (timing/cache), (ii) kernel- or hypervisor-level compromises, (iii) supply-chain attacks via compromised base images or dependencies, (iv) denial-of-service beyond configured CPU/memory/time limits, and (v) vulnerabilities in the container runtime itself. PyRlm’s contribution is to make execution semantics, constraints, and auditability explicit model components, enabling fail-closed engineering controls and reproducible analysis rather than guaranteeing absolute security.
---

### 8. Evaluation Framework (Option B: Systems-Level, Non-Quantitative)

Given the exploratory and architectural scope of PyRlm, we evaluate the system using systems-level evidence rather than benchmark-driven learning performance (e.g., reward curves or SOTA training throughput). Our evaluation focuses on four orthogonal dimensions: (E1) computational overhead, (E2) structural properties, (E3) expressiveness, and (E4) constraint enforcement. In this version, we report E2–E4 and treat E1 as future work due to environment-dependent variability in container runtime startup and reuse policies.

#### 8.1 Evaluation Criteria

We define the following evaluation axes:

**E1 — Computational Overhead**
What runtime cost is introduced by orchestration, tracing, and sandboxed execution relative to a minimal loop?

**E2 — Structural Systems Properties**
How does PyRlm differ from an ad-hoc agent loop with respect to explicit state transitions, traceability, isolation, and constraint modeling?

**E3 — Expressiveness**
Can heterogeneous agent patterns be implemented under the same RLM abstraction without modifying the orchestration layer?

**E4 — Constraint Enforcement & Safety**
Does the system enforce execution boundaries and output constraints under the defined threat model?

#### 8.2 E1 — Computational Overhead (Future Work)

A quantitative overhead study requires careful separation of (i) in-process orchestration and serialization costs from (ii) container cold-start latency, as well as explicit measurement of warm-start behavior under specific container reuse policies. These costs vary meaningfully across platforms and runtime configurations (e.g., Docker daemon settings, image cache state, gVisor runtime mode), and therefore require a dedicated experimental setup and reporting protocol to be interpretable.

For this reason, we defer E1 to future work and instead focus on E2–E4, which provide robust architectural evidence independent of absolute latency measurements. We note that PyRlm’s design explicitly prioritizes auditability, isolation, and controlled execution semantics over minimal overhead, and thus E1 should be interpreted as a trade-off analysis rather than a primary objective.

#### 8.3 E2 — Structural Systems Comparison

To contextualize PyRlm’s contribution at the systems level, we compare it against a “Minimal Agent Loop” implemented as a manual while cycle invoking exec() in-process, without isolation, structured tracing, or declarative constraints.

| Axis                          | Minimal Loop                       | PyRlm Orchestrator                                                       |
| :---------------------------- | :--------------------------------- | :----------------------------------------------------------------------- |
| **Decision Trace**            | Unstructured stdout logs           | **Structured event trace** (step, action, output, constraints, metrics)  |
| **Execution Isolation**       | None (host OS access)              | **Containerized execution** (Docker + gVisor)                            |
| **Constraint Modeling**       | Ad-hoc imperative checks           | **Declarative constraints** enforced at orchestration boundary           |
| **Failure Semantics**         | Implicit / mixed with control flow | **Explicit failure events** (`EXECUTION_FAILED`, `CONSTRAINT_TRIGGERED`) |
| **Reproducibility Artifacts** | None by default                    | **Serialized trace + configuration metadata**                            |

This comparison highlights PyRlm’s core shift: transforming implicit control-flow assumptions into explicit architectural components aligned with the RLM tuple (constraints, execution semantics, and observability).

#### 8.4 E3 — Expressiveness

We assess expressiveness by verifying whether diverse agent interaction patterns can be encoded without modifying the orchestration layer, i.e., by changing only the policy component ($\pi$) and/or constraint layer ($C$) while preserving the same transition and execution scaffolding.

In our case studies, PyRlm expressed representative patterns including:

- **Stateless question answering loops** (single-turn reasoning with minimal state mutation)

- **ReAct-style multi-step reasoning with tool invocation** (alternating decision and execution)

- **Context-aware data analysis** (persistent internal abstraction $\tilde{S}$ backed by structured memory or file-based context)

Across these scenarios, the orchestration abstraction remained unchanged: the system continued to implement the same Observe → Reason → Act → Feedback cycle, while the policy and constraints determined behavior. This supports the claim that the RLM tuple provides a sufficiently general architectural host for heterogeneous agent policies.

#### 8.5 E4 — Constraint Enforcement & Safety (Engineering Evidence)

To evaluate enforcement mechanisms under the threat model described in Section 7, we performed a controlled adversarial test in which an agent was instructed to access and print a sensitive environment variable (e.g., API_KEY).

- **Minimal Loop (no isolation):** If the variable exists in the host environment, it is accessible to in-process execution and may be printed.

- **PyRlm Sandbox:** Host environment variables are inaccessible due to container isolation, preventing direct host exfiltration via code execution.

- **Egress Filter:** If outputs match secret-detection rules (e.g., high-entropy patterns or explicit secret formats), they are redacted and the intervention is recorded as an explicit constraint event.

This experiment provides systems-level evidence that PyRlm enforces execution-boundary constraints and output filtering as designed. We emphasize that these results represent engineering containment and auditability within the sandboxed execution boundary; they do not constitute formal security proofs and do not cover out-of-scope threats (Section 7.2).

#### 8.6 Summary

PyRlm’s evaluation supports the claim that its primary contribution lies not in optimizing learning performance, but in enabling inspectable, enforceable, and reproducible agent systems via explicit modeling of constraints, execution semantics, and structured traces. While computational overhead analysis (E1) is deferred to future work, the structural and qualitative evidence (E2–E4) demonstrates that PyRlm operationalizes Reinforcement Learning Models as architectural constructs suitable for research into hybrid and safety-conscious agent systems.

---

### 9. Limitations

While PyRlm introduces a structured and inspectable architectural abstraction for Reinforcement Learning Models, several limitations must be acknowledged.

#### 9.1 Absence of Quantitative Overhead Analysis (E1)

This version of the paper does not include a comprehensive quantitative study of computational overhead (E1). In particular, we do not report controlled measurements of container cold-start latency, warm-start reuse policies, or fine-grained orchestration cost breakdowns across heterogeneous hardware environments.

Because sandbox runtime performance is highly dependent on container configuration, image caching state, host kernel behavior, and gVisor runtime settings, meaningful evaluation requires a dedicated benchmarking protocol with reproducible infrastructure conditions. Such a study is planned as future work. Accordingly, the current evaluation emphasizes structural and systems-level properties (E2–E4) rather than absolute latency metrics.

#### 9.2 Engineering-Level Security Guarantees

PyRlm provides controlled execution and constraint enforcement under a practical threat model, but it does not claim formal security guarantees or formal verification of isolation properties. The system relies on container-based isolation (Docker + gVisor) and output filtering mechanisms, which reduce risk but do not eliminate all classes of attack.

As discussed in Section 7, side-channel attacks, kernel-level exploits, supply-chain compromise, and vulnerabilities in container runtimes remain out of scope. PyRlm’s contribution lies in making execution boundaries explicit and auditable, not in proving end-to-end system security.

#### 9.3 Policy-Agnostic but Policy-Dependent Behavior

While the RLM abstraction is policy-agnostic, practical system behavior remains dependent on the selected policy component ($\pi$), including LLM-based reasoning systems. The correctness, robustness, and alignment properties of such policies are external to the architectural framework itself. PyRlm provides traceability and constraint enforcement, but does not guarantee semantic correctness of policy outputs.

#### 9.4 Single-Agent Focus

The current implementation focuses on single-agent orchestration loops. Although the RLM abstraction can conceptually generalize to multi-agent systems, distributed coordination, or hierarchical orchestration, such extensions are not yet implemented natively and require additional architectural layers.

#### 9.5 Research-Grade Status

PyRlm is released as research software (v0.1.0) and is subject to API evolution and architectural refinement. While the formal model presented here aims for conceptual rigor, empirical validation across diverse workloads and deployment settings remains ongoing work.

---

## 10. Conclusion

PyRlm bridges the gap between theoretical Reinforcement Learning models and practical, safe agent engineering. By treating the RLM as a first-class architectural construct—comprising defined states, actions, constraints, and execution boundaries—PyRlm enables researchers to build systems that are not only powerful but also inspectable, safe by design, and reproducible. We invite the community to explore this "model-centric" approach to AI agents.

---

## 11. References
Sutton, R. S., & Barto, A. G. (2018). Reinforcement Learning: An Introduction (2nd ed.). MIT Press.

Li, Y. (2017). Deep Reinforcement Learning: An Overview. arXiv:1701.07274.

Liang, E., et al. (2018). RLlib: Abstractions for Distributed Reinforcement Learning. arXiv:1712.09381.

Xi, Z., et al. (2023). The Rise and Potential of Large Language Model Based Agents: A Survey. arXiv:2309.07864.

Wu, Q., et al. (2023). AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation. arXiv:2308.08155.

Yao, S., et al. (2022). ReAct: Synergizing Reasoning and Acting in Language Models. arXiv:2210.03629.

Laird, J. E., Newell, A., & Rosenbloom, P. S. (1987). Soar: An Architecture for General Intelligence. Artificial Intelligence.

Amodei, D., et al. (2016). Concrete Problems in AI Safety. arXiv:1606.06565.

gVisor Team. (2018). gVisor: A Container Sandbox. (Project documentation/whitepaper).

---

## 12. Reproducibility

*   **Version**: PyRlm `v0.1.0`
*   **DOI**: 10.5281/zenodo.18568094
*   **Repository**: [https://github.com/1thirteeng3/PyRlm](https://github.com/1thirteeng3/PyRlm)
*   **Platform**: Tested on Linux (Ubuntu 22.04) with Docker Engine + gVisor (`runsc`).
*   **Commit**: `6104912`
*   **Reproduce**: `python scripts/benchmark_eval.py`
