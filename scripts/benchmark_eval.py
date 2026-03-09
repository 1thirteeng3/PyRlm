
import argparse
import asyncio
import csv
import json
import logging
import platform
import statistics
import time
import io
import contextlib
import statistics
import sys
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Any, Callable

# Add src to python path if needed (though running as -m is better, we'll facilitate script usage)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import docker
except ImportError:
    docker = None

from rlm.core.orchestrator import Orchestrator, OrchestratorConfig
from rlm.core.repl.docker import DockerSandbox, SandboxConfig, ExecutionResult
from rlm.security.egress import EgressFilter
from rlm.llm.base import BaseLLMClient, LLMResponse, Message, TokenUsage

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark")

# --- Constants & Snippets ---
FIB_SNIPPET = """def fib(n):
    a,b=0,1
    for _ in range(n):
        a,b=b,a+b
    return a
print(fib(10))"""

# Artifacts directory
ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(exist_ok=True)

# --- Mocks for Isolation ---

class MockLLMClient(BaseLLMClient):
    """
    Mock LLM that returns a deterministic code block.
    Used to benchmark Orchestrator overhead without network calls.
    """
    def __init__(self):
        super().__init__(api_key="mock", model="mock-model")

    @property
    def provider_name(self) -> str:
        return "mock"

    def complete(self, messages: list[Message], system_prompt: Optional[str] = None, **kwargs) -> LLMResponse:
        # Not used in async flow usually, but implemented for completeness
        return self._generate_response()

    def stream(self, messages: list[Message], system_prompt: Optional[str] = None, **kwargs):
        yield self._generate_response().content

    async def acomplete(self, messages: list[Message], system_prompt: Optional[str] = None, **kwargs) -> LLMResponse:
        return self._generate_response()

    async def astream(self, messages: list[Message], system_prompt: Optional[str] = None, **kwargs):
        yield self._generate_response().content

    def _generate_response(self) -> LLMResponse:
        # Wrap snippet in markdown code block
        content = f"Here is the code:\n```python\n{FIB_SNIPPET}\n```"
        return LLMResponse(
            content=content, 
            model="mock-model",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=50, total_tokens=60)
        )

class LocalSandbox:
    """
    Mock Sandbox that runs code locally using exec().
    Used to benchmark Orchestrator overhead without Docker.
    """
    def __init__(self):
        pass

    async def execute_async(self, code: str, context_mount: Optional[str] = None) -> ExecutionResult:
        # Run sync exec in thread to simulate async interface properly
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._execute_sync, code)

    def _execute_sync(self, code: str) -> ExecutionResult:
        f = io.StringIO()
        try:
            # Basic isolation of globals
            safe_globals = {"__builtins__": __builtins__}
            with contextlib.redirect_stdout(f):
                exec(code, safe_globals)
            stdout = f.getvalue()
            return ExecutionResult(stdout=stdout, stderr="", exit_code=0)
        except Exception as e:
            return ExecutionResult(stdout=f.getvalue(), stderr=str(e), exit_code=1)

# --- Benchmark Runner Class ---

@dataclass
class BenchmarkResult:
    config_name: str
    run_id: int
    latency_ms: float
    success: bool
    output_len: int

class BenchmarkRunner:
    def __init__(self, n: int, warmup: int):
        self.n = n
        self.warmup = warmup
        self.results: List[BenchmarkResult] = []

    def _measure_run(self, config_name: str, run_id: int, func: Callable) -> BenchmarkResult:
        t0 = time.perf_counter_ns()
        try:
            success, output_len = func()
        except Exception as e:
            logger.error(f"Run failed: {e}")
            success = False
            output_len = 0
        t1 = time.perf_counter_ns()
        
        latency_ms = (t1 - t0) / 1e6
        return BenchmarkResult(config_name, run_id, latency_ms, success, output_len)

    def run_config(self, config_name: str, func: Callable, is_cold_start: bool = False):
        logger.info(f"Starting config: {config_name}")
        
        # Warmup (skip for cold start logic if strict, but User asked for 5 warmups generally. 
        # For "Cold Start" config, user says "Cold start medido 10x". So no warmup for that specifically.)
        if not is_cold_start and self.warmup > 0:
            logger.info(f"  Running {self.warmup} warmups...")
            for _ in range(self.warmup):
                try:
                    func()
                except Exception:
                    pass

        # Actual runs
        n_runs = 10 if is_cold_start else self.n
        logger.info(f"  Running {n_runs} measured runs...")
        
        for i in range(n_runs):
            res = self._measure_run(config_name, i, func)
            self.results.append(res)
            # Optional small sleep to separate runs slightly
            time.sleep(0.01)

    def save_results(self):
        # CSV
        csv_path = ARTIFACTS_DIR / "bench_raw.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["config_name", "run_id", "latency_ms", "success", "output_len"])
            for r in self.results:
                writer.writerow([r.config_name, r.run_id, f"{r.latency_ms:.4f}", r.success, r.output_len])
        logger.info(f"Saved raw results to {csv_path}")

        # JSON Summary
        summary = {"env": self._get_env_info(), "results": {}}
        
        # Group by config
        configs = set(r.config_name for r in self.results)
        for cfg in configs:
            timings = [r.latency_ms for r in self.results if r.config_name == cfg]
            if not timings:
                continue
            
            median = statistics.median(timings)
            q1 = statistics.quantiles(timings, n=4)[0] if len(timings) >= 2 else min(timings)
            q3 = statistics.quantiles(timings, n=4)[2] if len(timings) >= 2 else max(timings)
            iqr = q3 - q1
            
            summary["results"][cfg] = {
                "n": len(timings),
                "median_ms": round(median, 4),
                "iqr_ms": [round(q1, 4), round(q3, 4)],
                "min_ms": round(min(timings), 4),
                "max_ms": round(max(timings), 4),
                "stdev": round(statistics.stdev(timings), 4) if len(timings) > 1 else 0
            }

        json_path = ARTIFACTS_DIR / "bench_summary.json"
        with open(json_path, "w") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Saved summary to {json_path}")

    def _get_env_info(self):
        env = {
            "python": sys.version,
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        }
        if docker:
            try:
                client = docker.from_env()
                env["docker_version"] = client.version().get("Version", "unknown")
            except:
                env["docker_version"] = "error"
        return env


# --- Configuration Implementations ---

def run_minimal_loop():
    """Config A: Minimal execution loop using exec()"""
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        exec(FIB_SNIPPET, {})
    return True, len(f.getvalue())

def run_orchestrator_trace():
    """Config B: PyRlm Orchestrator + Trace (no sandbox)"""
    # Setup
    llm = MockLLMClient()
    sandbox = LocalSandbox()
    config = OrchestratorConfig(max_iterations=1) # 1 iteration enough for snippet
    orchestrator = Orchestrator(llm_client=llm, sandbox=sandbox, config=config)
    
    # Execute
    # We use sync run() as wrapper since we want to measure full orchestrator overhead including async loop cost if any
    result = orchestrator.run("Calculate fib 10")
    
    output_len = len(result.steps[-1].output_data) if result.steps else 0
    return result.success, output_len

def run_sandbox_execution():
    """
    Config C/D: PyRlm Sandbox Execution.
    We instantiate a new DockerSandbox each time to be authentic to the library usage,
    but reuse the client connection implicit in library.
    """
    # Note: DockerSandbox creates a new container per execute() call.
    # The 'Cold' vs 'Warm' distinction here is purely process/daemon level cache.
    sandbox = DockerSandbox() 
    # Mocking agent_lib for local run if needed? 
    # DockerSandbox requires agent_lib to be mounted. 
    # Assumes we are running in repo root or have structure.
    # The benchmark script is in scripts/, repo root is parent. 
    # DockerSandbox.AGENT_LIB_PATH is relative to src/rlm/core/repl/docker.py
    # validation done in validation_security check.
    
    result = sandbox.execute(FIB_SNIPPET)
    return result.success, len(result.stdout)

# --- Egress Cost ---

def run_egress_cost(size_bytes: int):
    # Create random string of roughly size_bytes
    # 'a' * size to keep it simple/fast enough, or os.urandom for entropy?
    # User asked for: 1KB ('a'*1024), 10KB, 100KB.
    data = 'a' * size_bytes
    
    ef = EgressFilter()
    # Measure filter()
    _ = ef.filter(data)
    return True, len(data)

def run_egress_entropy():
    # "High-entropy like" (base64-ish)
    import secrets
    # 1KB of random base64
    data = secrets.token_urlsafe(1024) 
    ef = EgressFilter()
    _ = ef.filter(data)
    return True, len(data)


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="PyRlm Benchmark Suite")
    parser.add_argument("--n", type=int, default=30, help="Number of runs per config")
    parser.add_argument("--warmup", type=int, default=5, help="Number of warmup runs")
    args = parser.parse_args()

    runner = BenchmarkRunner(n=args.n, warmup=args.warmup)

    # 1. Minimal Loop
    runner.run_config("minimal_loop", run_minimal_loop)

    # 2. Orchestrator Trace (No Docker)
    runner.run_config("pyrlm_trace", run_orchestrator_trace)

    # 3. Sandbox Cold Start (First runs, effectively)
    # To properly simulate "Cold", ideally we'd restart things, but here we'll just run a separate batch
    # labeled "Cold". We skip warmup for this to capture the "first run" cost.
    runner.run_config("sandbox_cold", run_sandbox_execution, is_cold_start=True)

    # 4. Sandbox Warm Start
    # This runs AFTER the cold start batch, so the image/daemon are definitely warm.
    # We apply warmups here to stabilize.
    runner.run_config("sandbox_warm", run_sandbox_execution)

    # Optional: Egress Cost
    runner.run_config("egress_1kb", lambda: run_egress_cost(1024))
    runner.run_config("egress_10kb", lambda: run_egress_cost(10240))
    runner.run_config("egress_100kb", lambda: run_egress_cost(102400))
    runner.run_config("egress_entropy", run_egress_entropy)

    runner.save_results()

if __name__ == "__main__":
    main()
