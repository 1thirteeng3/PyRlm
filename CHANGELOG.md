# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-01-21

### Added
- **Async Foundation**: True async support with `aiodocker`
  - `AsyncDockerSandbox` class for non-blocking Docker operations
  - `Orchestrator.arun()` for async agent loops
  - `acomplete()` and `astream()` async methods in LLM clients
- **Robust Parsing**: State-machine markdown parser with mistletoe
  - `extract_python_code()` for reliable code block extraction
  - `extract_final_answer()` with multiple format support
  - `validate_python_syntax()` for pre-execution validation
- **Clean Boot Architecture**: In-container `agent_lib/` module
  - Standalone `ContextHandle` for in-container use
  - `boot.py` clean entry point
  - Volume mounting instead of string injection
- **Security Improvements**:
  - Binary output detection (magic bytes for PNG, ZIP, ELF, PDF, etc.)
  - Entropy allowlist to reduce false positives
  - `detect_binary_output()` function

### Changed
- **Fail-Closed Security**: gVisor now required by default
  - Raises `SecurityViolationError` if runsc not available
  - Use `allow_unsafe_runtime=True` for explicit override
- Docker sandbox now uses volume mounting for agent code
- Orchestrator uses robust parsing instead of regex

### Removed
- `ImportBlocker` class (Python-level false security)
- String-based code injection in Docker sandbox

### Dependencies
- Added `aiodocker>=0.21.0`
- Added `mistletoe>=1.2.0`
- Added `pip-audit>=2.6.0` (dev)

## [2.0.0] - 2026-01-21

### Added
- Initial v2.0 release with hardened security
- Docker sandbox with gVisor support
- Network isolation (`network_mode="none"`)
- Resource limits (memory, CPU, PIDs)
- Egress filtering (entropy, patterns, context echo)
- ContextHandle for memory-efficient file access
- Multi-provider LLM clients (OpenAI, Anthropic, Google)
- Budget management and cost tracking
- MkDocs documentation
- Comprehensive test suite

### Security
- OS-level isolation via Docker
- Automatic gVisor detection
- Shannon entropy secret detection
- Known secret pattern matching (AWS, JWT, private keys)
- Context echo prevention
