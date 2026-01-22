# Contributing to RLM-Python

Thank you for your interest in contributing to RLM-Python! This guide will help you get started.

## 🔒 Security Contributions

Security improvements are our **highest priority**. If you discover a vulnerability:

1. **Do NOT open a public issue**
2. Email security concerns privately to the maintainers
3. Allow 90 days for a fix before public disclosure

## 🚀 Getting Started

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
# Unit tests (no Docker required)
pytest tests/unit/ -v

# Integration tests (requires Docker)
pytest tests/integration/ -v

# Security tests (requires Docker + gVisor)
pytest tests/integration/ -v -m security

# All tests with coverage
pytest --cov=rlm --cov-report=html
```

## 📝 Code Style

We use `ruff` for linting and formatting:

```bash
# Format code
ruff format .

# Check linting
ruff check .

# Auto-fix issues
ruff check . --fix
```

## 🔄 Pull Request Process

1. **Fork** the repository
2. **Create a branch** for your feature (`git checkout -b feature/amazing-feature`)
3. **Make your changes** following the code style
4. **Write tests** for new functionality
5. **Run the test suite** to ensure nothing breaks
6. **Commit** with a descriptive message
7. **Push** to your fork
8. **Open a Pull Request**

### Commit Message Format

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Example:
```
feat(egress): add PDF magic byte detection

Detects PDF files in output to prevent binary exfiltration.
Closes #123
```

## 🏗️ Architecture Guidelines

### v3.0 Principles

1. **DRY**: All logic in `_execute_cycle()`, no duplication
2. **Fail-Fast**: Direct imports, no conditional fallbacks
3. **Async-First**: Use `async/await` for all I/O operations
4. **Defense in Depth**: Security at every layer

### Adding New Features

- **Egress Filters**: Add to `src/rlm/security/egress.py`
- **Parsing**: Modify `src/rlm/core/parsing.py` (mistletoe only!)
- **Docker Config**: Update `src/rlm/core/repl/docker.py`
- **Settings**: Add to `src/rlm/config/settings.py`

## 📚 Documentation

Update documentation when adding features:

- `README.md` - User-facing overview
- `docs/` - MkDocs detailed documentation
- Docstrings - Follow Google style

## 🙏 Thank You

Every contribution makes RLM more secure and reliable. We appreciate your time and effort!
