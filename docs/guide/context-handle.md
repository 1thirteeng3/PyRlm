# Context Handling

The `ContextHandle` class provides memory-efficient access to large files.

## Why ContextHandle?

When working with large context files (100MB, 1GB, or more), loading the entire file into memory is:

- **Slow** - Takes time to read
- **Expensive** - Uses lots of RAM
- **Risky** - Can crash with OOM

`ContextHandle` uses memory-mapping (`mmap`) for O(1) random access without loading the entire file.

## Basic Usage

```python
from rlm import ContextHandle

with ContextHandle("/path/to/large_file.txt") as ctx:
    print(f"File size: {ctx.size_mb:.2f} MB")
    
    # Read first 1000 bytes
    header = ctx.head(1000)
    
    # Read last 1000 bytes
    footer = ctx.tail(1000)
```

## Search API

Find patterns without reading the entire file:

```python
ctx = ContextHandle("/path/to/logs.txt")

# Search with regex
matches = ctx.search(r"ERROR.*timeout", max_results=10)

for offset, match_text in matches:
    print(f"Found at byte {offset}: {match_text}")
    
    # Get surrounding context
    snippet = ctx.snippet(offset, window=500)
    print(snippet)
```

## Line-Based Search

```python
# Search and get line numbers
matches = ctx.search_lines(r"CRITICAL", max_results=5)

for line_num, line, context in matches:
    print(f"Line {line_num}: {line}")
```

## Windowed Reading

Read specific portions:

```python
# Read around a specific offset
text = ctx.read_window(offset=50000, radius=500)

# Or using snippet
text = ctx.snippet(offset=50000, window=1000)

# Read exact range
text = ctx.read(start=1000, length=500)
```

## Iterating Lines

For streaming access:

```python
for line_num, line in ctx.iterate_lines(start_line=100):
    if line_num > 200:
        break
    process(line)
```

## API Reference

```python
class ContextHandle:
    size: int           # Total size in bytes
    size_mb: float      # Size in megabytes
    path: Path          # File path
    
    def read(start: int, length: int) -> str
    def read_window(offset: int, radius: int = 500) -> str
    def snippet(offset: int, window: int = 500) -> str
    def head(n_bytes: int = 1000) -> str
    def tail(n_bytes: int = 1000) -> str
    
    def search(pattern: str, max_results: int = 10) -> List[Tuple[int, str]]
    def search_lines(pattern: str, max_results: int = 10) -> List[Tuple[int, str, str]]
    
    def iterate_lines(start_line: int = 1) -> Iterator[Tuple[int, str]]
    
    def close() -> None
```

## In the Sandbox

When mounted in the Docker sandbox, use the `ctx` global variable:

```python
# Inside sandbox execution
matches = ctx.search(r"important pattern")
for offset, match in matches:
    print(ctx.snippet(offset))
```
