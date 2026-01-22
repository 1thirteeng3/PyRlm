# Async/Await Guide

RLM v3.0 is **async-first**. Learn how to leverage non-blocking execution.

## Why Async?

| Sync (`run()`) | Async (`arun()`) |
|----------------|------------------|
| Blocks the thread | Non-blocking |
| One request at a time | Concurrent requests |
| Simple scripts | Web servers, APIs |

## Basic Async

```python
import asyncio
from rlm import Orchestrator

async def main():
    agent = Orchestrator()
    
    result = await agent.arun("Calculate fibonacci(20)")
    print(result.final_answer)

asyncio.run(main())
```

## Concurrent Execution

Process multiple queries simultaneously:

```python
import asyncio
from rlm import Orchestrator

async def process_query(agent: Orchestrator, query: str) -> str:
    result = await agent.arun(query)
    return result.final_answer

async def main():
    agent = Orchestrator()
    
    queries = [
        "What is 2 + 2?",
        "What is 10 * 10?",
        "What is sqrt(144)?",
    ]
    
    # Execute all concurrently
    results = await asyncio.gather(*[
        process_query(agent, q) for q in queries
    ])
    
    for query, answer in zip(queries, results):
        print(f"{query} → {answer}")

asyncio.run(main())
```

## FastAPI Integration

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from rlm import Orchestrator
from rlm.core.exceptions import RLMError

app = FastAPI()
orchestrator = Orchestrator()

class QueryRequest(BaseModel):
    query: str
    context_path: str | None = None

class QueryResponse(BaseModel):
    answer: str
    success: bool
    iterations: int

@app.post("/execute", response_model=QueryResponse)
async def execute(request: QueryRequest):
    try:
        result = await orchestrator.arun(
            request.query,
            context_path=request.context_path,
        )
        return QueryResponse(
            answer=result.final_answer or "",
            success=result.success,
            iterations=result.iterations,
        )
    except RLMError as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## aiohttp Integration

```python
from aiohttp import web
from rlm import Orchestrator

orchestrator = Orchestrator()

async def handle_execute(request: web.Request) -> web.Response:
    data = await request.json()
    query = data.get("query", "")
    
    result = await orchestrator.arun(query)
    
    return web.json_response({
        "answer": result.final_answer,
        "success": result.success,
    })

app = web.Application()
app.router.add_post("/execute", handle_execute)
```

## Architecture Note

v3.0 uses a **Single Source of Truth** architecture:

```python
# Internal structure
async def _execute_cycle(self, ...):
    """All logic lives here"""
    
async def arun(self, ...):
    """Public async - delegates to _execute_cycle"""
    return await self._execute_cycle(...)

def run(self, ...):
    """Public sync - pure wrapper"""
    return asyncio.run(self.arun(...))
```

This ensures:

- ✅ Zero code duplication
- ✅ Consistent behavior sync/async
- ✅ All fixes apply to both paths

## Running in Jupyter

If you're in Jupyter/IPython (which has a running event loop):

```python
# Option 1: Use nest_asyncio
import nest_asyncio
nest_asyncio.apply()

result = orchestrator.run("query")

# Option 2: Use await directly (preferred)
result = await orchestrator.arun("query")
```

## CPU Offloading

v3.0 runs CPU-intensive operations (egress filtering) in a thread pool:

```python
# This happens automatically - you don't need to do anything
# But here's what's happening internally:

loop = asyncio.get_running_loop()
result = await loop.run_in_executor(
    None,  # Uses default ThreadPoolExecutor
    self.egress_filter.filter,
    output_text,
)
```

This prevents large outputs from blocking your event loop.
