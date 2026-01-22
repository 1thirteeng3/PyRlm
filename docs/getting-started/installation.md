# Installation

Complete installation guide for RLM-Python.

## Requirements

- **Python**: 3.10, 3.11, or 3.12
- **Docker Engine**: Required for sandbox execution
- **gVisor** (optional): Recommended for production security

## Install the Package

```bash
pip install rlm-python
```

## Docker Setup

### Linux

```bash
# Install Docker Engine
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Verify installation
docker run hello-world
```

### macOS

Download and install [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/).

### Windows

Download and install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/) with WSL 2 backend.

## gVisor Installation (Production)

!!! tip "Recommended for Production"
    gVisor provides kernel-level syscall interception, blocking dangerous operations before they reach your host.

### Linux (Ubuntu/Debian)

```bash
# Add gVisor repository
curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" | sudo tee /etc/apt/sources.list.d/gvisor.list > /dev/null

# Install runsc
sudo apt-get update && sudo apt-get install -y runsc

# Configure Docker
sudo runsc install
sudo systemctl restart docker

# Verify
docker run --runtime=runsc hello-world
```

### Without gVisor

If you can't install gVisor, you can explicitly allow unsafe runtime:

```bash
export RLM_ALLOW_UNSAFE_RUNTIME=1
```

!!! danger "Security Warning"
    Running without gVisor provides reduced isolation. The code still runs in Docker containers with network disabled, but syscall-level protection is not available.

## LLM Provider Setup

RLM supports multiple LLM providers. Set your API key:

=== "OpenAI"
    ```bash
    export OPENAI_API_KEY=sk-...
    export RLM_LLM_PROVIDER=openai
    export RLM_LLM_MODEL=gpt-4
    ```

=== "Anthropic"
    ```bash
    export ANTHROPIC_API_KEY=sk-ant-...
    export RLM_LLM_PROVIDER=anthropic
    export RLM_LLM_MODEL=claude-3-opus
    ```

=== "Google"
    ```bash
    export GOOGLE_API_KEY=...
    export RLM_LLM_PROVIDER=google
    export RLM_LLM_MODEL=gemini-pro
    ```

## Verify Installation

```python
from rlm import Orchestrator, settings

# Check configuration
print(f"Docker Image: {settings.docker_image}")
print(f"LLM Provider: {settings.llm_provider}")

# Test execution
agent = Orchestrator()
result = agent.run("Print 'Hello, RLM!'")
print(result.final_answer)
```

## Troubleshooting

??? question "Docker permission denied"
    Add your user to the docker group:
    ```bash
    sudo usermod -aG docker $USER
    newgrp docker
    ```

??? question "gVisor not detected"
    Check if runsc is installed:
    ```bash
    runsc --version
    docker info | grep -i runtime
    ```

??? question "LLM API errors"
    Verify your API key is set:
    ```bash
    echo $OPENAI_API_KEY  # Should not be empty
    ```
