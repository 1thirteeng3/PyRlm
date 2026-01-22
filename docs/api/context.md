# Context Handle

::: rlm.core.memory.handle.ContextHandle
    handler: python
    options:
      members:
        - __init__
        - read
        - read_window
        - snippet
        - search
        - search_lines
        - iterate_lines
        - head
        - tail
        - size
        - size_mb
      show_root_full_path: false
      show_source: true

## Overview

`ContextHandle` provides memory-efficient access to large files using `mmap`. The LLM never loads the entire file into memory.

## Usage

### Creating a Handle

```python
from rlm.core.memory import ContextHandle

# Open a large file
ctx = ContextHandle("/path/to/large_file.csv")

print(f"File size: {ctx.size_mb:.2f} MB")
```

### Searching

```python
# Find all occurrences of a pattern
matches = ctx.search(r"ERROR.*timeout", max_results=10)

for offset, matched_text in matches:
    # Get context around the match
    snippet = ctx.snippet(offset, window=500)
    print(f"Found at {offset}: {snippet}")
```

### Reading Sections

```python
# Read first 1KB
header = ctx.head(n_bytes=1024)

# Read last 1KB
footer = ctx.tail(n_bytes=1024)

# Read specific range
chunk = ctx.read(start=5000, length=2000)
```

### Streaming Lines

```python
# Memory-efficient line iteration
for line_no, line in ctx.iterate_lines(start_line=100):
    if "important" in line:
        print(f"Line {line_no}: {line}")
    if line_no > 200:
        break
```

## Binary Detection

v3.0 detects binary files and raises `ContextError`:

```python
from rlm.core.memory import ContextHandle
from rlm.core.exceptions import ContextError

try:
    ctx = ContextHandle("/path/to/image.png")
except ContextError as e:
    print(e)  # "Binary file detected via null bytes..."
```

This prevents the LLM from receiving garbage input that would cause hallucination.

## With Orchestrator

```python
from rlm import Orchestrator

agent = Orchestrator()

result = await agent.arun(
    query="Find all customers with revenue > $100,000",
    context_path="/path/to/customers.csv"  # Uses ContextHandle internally
)
```
