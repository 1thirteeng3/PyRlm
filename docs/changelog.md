# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-01-22

### The Perfection Update 🎯

v3.0 focuses on architectural perfection: DRY code, strict parsing, resource safety, and non-blocking I/O.

### Added

- **Phase 1: DRY Unification**
  - `_execute_cycle()` as Single Source of Truth
  - `run()` is now a pure sync wrapper (no duplicated logic)
  - Zero code duplication between sync/async paths

- **Phase 4: CPU Offloading**
  - Egress filtering runs in `ThreadPoolExecutor`
  - `run_in_executor` for non-blocking Shannon entropy calculation
  - Large outputs no longer block the event loop

- **Phase 5: Context Safety**
  - Binary file detection on `ContextHandle` initialization
  - Null bytes and control character detection
  - Prevents LLM hallucination on garbage input

### Changed

- **Phase 2: Strict Parsing**
  - Direct `mistletoe` import (fail-fast if missing)
  - Removed all regex fallback code
  - Pure AST parsing for deterministic behavior

- **Phase 3: Resource Safety**
  - `TemporaryDirectory` replaces `NamedTemporaryFile`
  - Auto-cleanup even on SIGKILL
  - No temp file leaks possible

### Removed

- `HAS_MISTLETOE` conditional import
- `extract_code_blocks_regex()` fallback function
- Manual temp file cleanup in `finally` blocks

---

## [2.1.0] - 2026-01-21

### Async & Hardening Update

### Added

- **Async Foundation**
  - `aiodocker` for true async Docker operations
  - `AsyncDockerSandbox` class
  - `Orchestrator.arun()` for async agent loops
  - `acomplete()` and `astream()` in LLM clients

- **Robust Parsing**
  - State machine parser (`parsing.py`)
  - `mistletoe` integration for edge cases
  - `extract_python_code()` for reliable extraction

- **Clean Boot Architecture**
  - `agent_lib/` module for in-container code
  - Volume mounting instead of string injection
  - `boot.py` clean entry point

- **Security Hardening**
  - Binary output detection (magic bytes)
  - Entropy allowlist for hashes/UUIDs
  - Fail-closed: gVisor required by default

### Changed

- Docker sandbox uses volume mounting for agent code
- Orchestrator uses robust parsing instead of basic regex

### Removed

- `ImportBlocker` class (Python-level false security)
- String-based code injection

---

## [2.0.0] - 2026-01-21

### Initial Release 🚀

- Docker sandbox with gVisor support
- Network isolation (`network_mode="none"`)
- Resource limits (memory, CPU, PIDs)
- Egress filtering (entropy, patterns, context echo)
- ContextHandle for memory-efficient file access
- Multi-provider LLM clients (OpenAI, Anthropic, Google)
- Budget management and cost tracking
- Comprehensive test suite
