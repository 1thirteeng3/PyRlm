# Contributing

Guidelines for contributing to RLM-Python.

!!! tip "Security First"
    Security improvements are our **highest priority**. If you discover a vulnerability, please report it privately.

## Getting Started

### Prerequisites

- Python 3.10+
- Docker Engine
- gVisor (optional, for security tests)

### Development Setup

```bash
# Clone the repository
git clone https://github.com/1thirteeng3/PyRlm.git
cd PyRlm

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install in development mode
pip install -e ".[dev]"
```

### Running Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires Docker)
pytest tests/integration/ -v

# All tests with coverage
pytest --cov=rlm --cov-report=html
```

## Code Style

We use `ruff` for linting and formatting:

```bash
ruff format .
ruff check . --fix
```

## Pull Request Process

1. **Fork** the repository
2. **Create a branch**: `git checkout -b feature/amazing-feature`
3. **Write tests** for new functionality
4. **Run the test suite**
5. **Commit**: `git commit -m "feat(scope): description"`
6. **Push** and open a Pull Request

### Commit Format

```
type(scope): description

Types: feat, fix, docs, style, refactor, test, chore
```

## v3.0 Architecture Principles

1. **DRY**: All logic in `_execute_cycle()`, no duplication
2. **Fail-Fast**: Direct imports, no conditional fallbacks
3. **Async-First**: Use `async/await` for all I/O operations
4. **Defense in Depth**: Security at every layer

---

**Thank you for contributing!** 🙏
