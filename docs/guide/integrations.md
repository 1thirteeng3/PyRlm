# Integrations

Use RLM with popular frameworks.

## LangChain

Use RLM as a LangChain tool:

```python
from langchain.agents import Tool
from langchain.agents import initialize_agent
from langchain.llms import OpenAI
from rlm import Orchestrator

# Create RLM tool
rlm_agent = Orchestrator()

def execute_code(query: str) -> str:
    result = rlm_agent.run(query)
    return result.final_answer or result.error or "No result"

tools = [
    Tool(
        name="SecureCodeExecution",
        func=execute_code,
        description="Execute Python code securely in a sandbox. "
                    "Use for calculations, data analysis, etc."
    )
]

# Create LangChain agent
llm = OpenAI(temperature=0)
agent = initialize_agent(tools, llm, agent="zero-shot-react-description")

# Use it
result = agent.run("Calculate the first 10 fibonacci numbers")
```

## CrewAI

```python
from crewai import Agent, Task, Crew
from rlm import Orchestrator

rlm = Orchestrator()

def secure_execute(code_request: str) -> str:
    result = rlm.run(code_request)
    return result.final_answer

# Create agent with RLM capability
analyst = Agent(
    role="Data Analyst",
    goal="Analyze data securely",
    backstory="Expert data analyst with secure execution environment",
    tools=[secure_execute],
)

task = Task(
    description="Analyze the sales data and find trends",
    agent=analyst,
)

crew = Crew(agents=[analyst], tasks=[task])
result = crew.kickoff()
```

## Celery (Background Tasks)

```python
from celery import Celery
from rlm import Orchestrator

app = Celery('tasks', broker='redis://localhost:6379')

@app.task
def execute_query(query: str, context_path: str = None) -> dict:
    agent = Orchestrator()
    result = agent.run(query, context_path=context_path)
    
    return {
        "answer": result.final_answer,
        "success": result.success,
        "iterations": result.iterations,
    }

# Usage
task = execute_query.delay("Calculate sqrt(144)")
result = task.get()  # {"answer": "12.0", "success": True, ...}
```

## Streamlit

```python
import streamlit as st
import asyncio
from rlm import Orchestrator

st.title("🛡️ RLM Secure Executor")

# Initialize (cached)
@st.cache_resource
def get_agent():
    return Orchestrator()

agent = get_agent()

# User input
query = st.text_area("Enter your query:", height=100)

if st.button("Execute"):
    with st.spinner("Running in secure sandbox..."):
        result = agent.run(query)
        
    if result.success:
        st.success(f"**Answer:** {result.final_answer}")
    else:
        st.error(f"Error: {result.error}")
    
    with st.expander("Execution Details"):
        st.json({
            "iterations": result.iterations,
            "steps": len(result.steps),
            "budget": result.budget_summary,
        })
```

## Jupyter Notebooks

```python
# Install nest_asyncio for Jupyter compatibility
!pip install nest_asyncio

import nest_asyncio
nest_asyncio.apply()

from rlm import Orchestrator

agent = Orchestrator()

# Now you can use sync interface in Jupyter
result = agent.run("Plot a sine wave from 0 to 2π")
print(result.final_answer)
```

Or use async directly:

```python
result = await agent.arun("What is 2 + 2?")
```

## Django

```python
# views.py
from django.http import JsonResponse
from django.views import View
from rlm import Orchestrator
import asyncio

class ExecuteView(View):
    def post(self, request):
        query = request.POST.get("query", "")
        
        agent = Orchestrator()
        
        # Run async in sync context
        result = asyncio.run(agent.arun(query))
        
        return JsonResponse({
            "answer": result.final_answer,
            "success": result.success,
        })
```

For async Django (ASGI):

```python
# views.py (async)
from django.http import JsonResponse
from rlm import Orchestrator

async def execute_view(request):
    query = request.POST.get("query", "")
    
    agent = Orchestrator()
    result = await agent.arun(query)
    
    return JsonResponse({
        "answer": result.final_answer,
        "success": result.success,
    })
```
