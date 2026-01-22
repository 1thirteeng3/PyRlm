# Context Files

Work with large files without loading them into memory.

## Overview

RLM uses `ContextHandle` to provide memory-efficient access to large files. The LLM receives tools to search and read snippets, never loading the entire file.

## Basic Usage

```python
from rlm import Orchestrator

agent = Orchestrator()

result = await agent.arun(
    query="Find all error messages in this log file",
    context_path="/var/log/app.log"  # 500MB log file
)
```

Internally, RLM:

1. Creates a `ContextHandle` with mmap
2. Provides search/read methods to the LLM
3. The LLM searches for patterns
4. Reads only relevant snippets

## How the LLM Uses Context

The LLM receives code tools like:

```python
# Search for patterns
matches = ctx.search(r"ERROR|CRITICAL", max_results=10)

# Read snippets around matches
for offset, match_text in matches:
    snippet = ctx.snippet(offset, window=500)
    print(snippet)
```

## Direct ContextHandle Usage

```python
from rlm.core.memory import ContextHandle

# Open a large file
ctx = ContextHandle("/path/to/data.csv")

print(f"Size: {ctx.size_mb:.2f} MB")

# Search for patterns
matches = ctx.search(r"revenue > 1000000")

# Read around matches
for offset, match in matches:
    print(ctx.read_window(offset, radius=200))

# Stream lines (memory efficient)
for line_no, line in ctx.iterate_lines():
    if "important" in line:
        print(f"Line {line_no}: {line}")
```

## Supported Files

### ✅ Text Files

- Log files (.log, .txt)
- CSV files (.csv)
- JSON files (.json)
- Source code (.py, .js, etc.)
- Markdown (.md)

### ❌ Binary Files (v3.0+)

RLM v3.0 **rejects binary files**:

```python
from rlm.core.memory import ContextHandle
from rlm.core.exceptions import ContextError

try:
    ctx = ContextHandle("/path/to/image.png")
except ContextError as e:
    print(e)  # "Binary file detected via null bytes..."
```

This prevents LLM hallucination on garbage input.

## Large File Tips

### 1. Use Specific Queries

```python
# ❌ Too vague - LLM might try to read everything
result = await agent.arun(
    "Tell me about this file",
    context_path="huge_data.csv"
)

# ✅ Specific - LLM searches for relevant data
result = await agent.arun(
    "Find the top 5 customers by total_revenue column",
    context_path="huge_data.csv"
)
```

### 2. Provide Structure Hints

```python
# ✅ Tell the LLM about the file format
result = await agent.arun(
    "This CSV has columns: id, name, email, revenue. "
    "Find all customers with revenue > 100000",
    context_path="customers.csv"
)
```

### 3. Check File Size First

```python
from rlm.core.memory import ContextHandle

ctx = ContextHandle("/path/to/file.csv")

if ctx.size_mb > 100:
    print(f"Warning: Large file ({ctx.size_mb:.0f} MB)")
    print("Consider pre-processing or sampling")
```

## Memory Efficiency

ContextHandle uses `mmap` for zero-copy access:

```
┌───────────────────────────────┐
│     Virtual Memory Space      │
├───────────────────────────────┤
│  ContextHandle.read(100, 50)  │  ← Only maps 50 bytes
├───────────────────────────────┤
│          Physical File        │  ← 10GB on disk
│       (memory-mapped)         │
└───────────────────────────────┘
```

No matter how large the file, memory usage stays constant.
