# Installation

## Requirements

- **Python 3.10+**
- **Docker** (for sandbox execution)
- **Optional**: gVisor (`runsc`) for enhanced isolation

## Installation Methods

### From PyPI (Recommended)

```bash
pip install rlm-python
```

### With Development Dependencies

```bash
pip install "rlm-python[dev]"
```

This includes:
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `mypy` - Type checking
- `ruff` - Linting

### From Source

```bash
git clone https://github.com/rlm-python/rlm.git
cd rlm
pip install -e ".[dev]"
```

## Docker Setup

RLM requires Docker for sandboxed code execution.

### Windows

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. Start Docker Desktop
3. Verify installation:
   ```bash
   docker run hello-world
   ```

### Linux

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Add user to docker group
sudo usermod -aG docker $USER

# Verify
docker run hello-world
```

### macOS

1. Install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)
2. Start Docker from Applications
3. Verify with `docker run hello-world`

## Optional: gVisor Installation

gVisor provides an additional security layer by intercepting syscalls in userspace.

### Linux Only

```bash
# Download runsc
curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" | sudo tee /etc/apt/sources.list.d/gvisor.list > /dev/null
sudo apt-get update && sudo apt-get install -y runsc

# Configure Docker
sudo runsc install
sudo systemctl restart docker
```

!!! note "Windows/macOS"
    gVisor is only available on Linux. On Windows/macOS, RLM automatically falls back to standard Docker isolation with enhanced security options.

## Verify Installation

```python
from rlm import DockerSandbox, settings

# Check configuration
print(f"Provider: {settings.api_provider}")
print(f"Execution Mode: {settings.execution_mode}")

# Check Docker sandbox
sandbox = DockerSandbox()
security = sandbox.validate_security()
print(f"Docker Available: {security['docker_available']}")
print(f"gVisor Available: {security['gvisor_available']}")
```
