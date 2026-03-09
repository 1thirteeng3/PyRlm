"""
Cost Management and Budget Tracking.

This module provides tools for tracking API costs and enforcing
spending limits to prevent runaway costs.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from rlm.config.settings import settings
from rlm.core.exceptions import BudgetExceededError

logger = logging.getLogger(__name__)


# Fallback pricing when external file is not available
DEFAULT_PRICING = {
    "gpt-4-turbo": {"input_cost_per_m": 10.00, "output_cost_per_m": 30.00},
    "gpt-4o": {"input_cost_per_m": 5.00, "output_cost_per_m": 15.00},
    "gpt-4o-mini": {"input_cost_per_m": 0.15, "output_cost_per_m": 0.60},
    "gpt-4o-2024-11-20": {"input_cost_per_m": 2.50, "output_cost_per_m": 10.00},
    "o4-mini": {"input_cost_per_m": 1.10, "output_cost_per_m": 4.40},
    "o3-pro": {"input_cost_per_m": 20.00, "output_cost_per_m": 40.00},
    "o3": {"input_cost_per_m": 2.00, "output_cost_per_m": 8.00},
    "o3-mini": {"input_cost_per_m": 1.10, "output_cost_per_m": 4.40},
    "gpt-4.1": {"input_cost_per_m": 2.00, "output_cost_per_m": 8.00},
    "gpt-4.1-mini": {"input_cost_per_m": 0.40, "output_cost_per_m": 1.60},
    "gpt-4.1-nano": {"input_cost_per_m": 0.10, "output_cost_per_m": 0.40},
    "gpt-5": {"input_cost_per_m": 1.25, "output_cost_per_m": 10.00},
    "gpt-5-mini": {"input_cost_per_m": 0.25, "output_cost_per_m": 2.00},
    "gpt-5-nano": {"input_cost_per_m": 0.05, "output_cost_per_m": 0.40},
    "gpt-5-codex": {"input_cost_per_m": 1.25, "output_cost_per_m": 10.00},
    "gpt-5.1": {"input_cost_per_m": 1.25, "output_cost_per_m": 10.00},
    "gpt-5.1-codex": {"input_cost_per_m": 1.25, "output_cost_per_m": 10.00},
    "gpt-5.1-codex-max": {"input_cost_per_m": 1.25, "output_cost_per_m": 10.00},
    "gpt-5.1-chat-latest": {"input_cost_per_m": 1.25, "output_cost_per_m": 10.00},
    "gpt-5.2": {"input_cost_per_m": 1.75, "output_cost_per_m": 14.00},
    "gpt-5.2-chat-latest": {"input_cost_per_m": 1.75, "output_cost_per_m": 14.00},
    "gpt-5.2-codex": {"input_cost_per_m": 1.75, "output_cost_per_m": 14.00},
    "gpt-5.3-chat-latest": {"input_cost_per_m": 1.75, "output_cost_per_m": 14.00},
    "gpt-5.3-codex": {"input_cost_per_m": 1.75, "output_cost_per_m": 14.00},
    "gpt-5.3-codex-xhigh": {"input_cost_per_m": 1.75, "output_cost_per_m": 14.00},
    "gpt-5.4": {"input_cost_per_m": 2.50, "output_cost_per_m": 15.00},
    "openai/gpt-oss-120b": {"input_cost_per_m": 0.08, "output_cost_per_m": 0.44},
    "claude-3-opus": {"input_cost_per_m": 15.00, "output_cost_per_m": 75.00},
    "claude-3-sonnet": {"input_cost_per_m": 3.00, "output_cost_per_m": 15.00},
    "claude-3-sonnet-20240229": {"input_cost_per_m": 3.00, "output_cost_per_m": 15.00},
    "claude-3-7-sonnet-20250219": {"input_cost_per_m": 3.00, "output_cost_per_m": 15.00},
    "claude-sonnet-4-20250514": {"input_cost_per_m": 3.00, "output_cost_per_m": 15.00},
    "claude-opus-4-20250514": {"input_cost_per_m": 15.00, "output_cost_per_m": 75.00},
    "claude-opus-4-1-20250805": {"input_cost_per_m": 15.00, "output_cost_per_m": 75.00},
    "claude-sonnet-4-5-20250929": {"input_cost_per_m": 3.00, "output_cost_per_m": 15.00},
    "claude-haiku-4-5-20251001": {"input_cost_per_m": 1.00, "output_cost_per_m": 5.00},
    "claude-opus-4-5-20251101": {"input_cost_per_m": 5.00, "output_cost_per_m": 25.00},
    "claude-opus-4-6": {"input_cost_per_m": 5.00, "output_cost_per_m": 25.00},
    "claude-sonnet-4-6": {"input_cost_per_m": 3.00, "output_cost_per_m": 15.00},
    "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8": {"input_cost_per_m": 0.14, "output_cost_per_m": 0.59},
    "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo": {"input_cost_per_m": 3.50, "output_cost_per_m": 3.50},
    "meta-llama/Meta-Llama-3.1-8B-Instruct": {"input_cost_per_m": 0.02, "output_cost_per_m": 0.05},
    "llama-3.3-70b-versatile": {"input_cost_per_m": 0.59, "output_cost_per_m": 0.79},
    "gemini-1.5-pro": {"input_cost_per_m": 3.50, "output_cost_per_m": 10.50},
    "gemini-2.5-pro": {"input_cost_per_m": 1.25, "output_cost_per_m": 10.00},
    "gemini-2.5-flash": {"input_cost_per_m": 0.30, "output_cost_per_m": 2.50},
    "gemini-3.1-pro-preview": {"input_cost_per_m": 2.00, "output_cost_per_m": 12.00},
    "gemini-3-flash-preview": {"input_cost_per_m": 0.50, "output_cost_per_m": 3.00},
    "gemini-3.1-flash-lite-preview": {"input_cost_per_m": 0.25, "output_cost_per_m": 1.50},
    "qwen-2.5-coder-32b": {"input_cost_per_m": 0.79, "output_cost_per_m": 0.79},
    "Qwen/Qwen2.5-72B-Instruct": {"input_cost_per_m": 0.11, "output_cost_per_m": 0.38},
    "Qwen/QwQ-32B": {"input_cost_per_m": 0.40, "output_cost_per_m": 0.40},
    "Qwen/Qwen3-235B-A22B-Instruct-2507": {"input_cost_per_m": 0.13, "output_cost_per_m": 0.60},
    "Qwen/Qwen3-32B": {"input_cost_per_m": 0.09, "output_cost_per_m": 0.29},
    "qwen/qwen3-coder-480b-a35b-instruct": {"input_cost_per_m": 0.29, "output_cost_per_m": 1.20},
    "qwen3-max": {"input_cost_per_m": 1.20, "output_cost_per_m": 6.00},
    "grok-4-0709": {"input_cost_per_m": 3.00, "output_cost_per_m": 15.00},
    "grok-4-fast-non-reasoning": {"input_cost_per_m": 0.20, "output_cost_per_m": 0.50},
    "grok-4-1-fast-non-reasoning": {"input_cost_per_m": 0.20, "output_cost_per_m": 0.50},
    "grok-code-fast-1": {"input_cost_per_m": 0.20, "output_cost_per_m": 1.50},
    "kimi-k2-turbo-preview": {"input_cost_per_m": 0.15, "output_cost_per_m": 8.00},
    "kimi-k2.5": {"input_cost_per_m": 0.60, "output_cost_per_m": 3.00},
    "deepseek/deepseek-v3.1": {"input_cost_per_m": 0.55, "output_cost_per_m": 1.66},
    "deepseek-ai/DeepSeek-V3.1-Terminus": {"input_cost_per_m": 0.27, "output_cost_per_m": 1.00},
    "deepseek-ai/DeepSeek-R1": {"input_cost_per_m": 3.00, "output_cost_per_m": 7.00},
    "deepseek-ai/DeepSeek-V3.2": {"input_cost_per_m": 0.27, "output_cost_per_m": 0.40},
    "zai-org/glm-4.5": {"input_cost_per_m": 0.60, "output_cost_per_m": 2.20},
    "zai-org/glm-4.6": {"input_cost_per_m": 0.60, "output_cost_per_m": 2.20},
    "zai-org/glm-4.7": {"input_cost_per_m": 0.60, "output_cost_per_m": 2.20},
    "zai-org/glm-5": {"input_cost_per_m": 1.00, "output_cost_per_m": 3.20},
}


@dataclass
class PricingData:
    """Pricing information for a model."""

    input_cost_per_million: float
    output_cost_per_million: float

    def calculate_cost(self, input_tokens: Optional[int], output_tokens: Optional[int]) -> float:
        """
        Calculate the cost for a given number of tokens.

        Args:
            input_tokens: Number of input/prompt tokens
            output_tokens: Number of output/completion tokens

        Returns:
            Total cost in USD
        """
        in_toks = input_tokens or 0
        out_toks = output_tokens or 0

        input_cost = (in_toks / 1_000_000) * self.input_cost_per_million
        output_cost = (out_toks / 1_000_000) * self.output_cost_per_million
        return input_cost + output_cost


@dataclass
class UsageRecord:
    """Record of a single API usage."""

    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    timestamp: Optional[str] = None


@dataclass
class BudgetManager:
    """
    Manages API spending and enforces budget limits.

    Tracks cumulative costs across multiple API calls and raises
    an exception when the budget limit is exceeded.

    Example:
        >>> budget = BudgetManager(limit_usd=5.0)
        >>> budget.record_usage("gpt-4o", input_tokens=1000, output_tokens=500)
        >>> print(f"Spent: ${budget.total_spent:.4f}")
    """

    limit_usd: float = field(default_factory=lambda: settings.cost_limit_usd)
    pricing: dict[str, PricingData] = field(default_factory=dict)
    history: list[UsageRecord] = field(default_factory=list)
    total_spent: float = 0.0

    def __post_init__(self) -> None:
        """Load pricing data after initialization."""
        if not self.pricing:
            self.pricing = self._load_pricing()

    def _load_pricing(self) -> dict[str, PricingData]:
        """
        Load pricing data from external file or fallback to defaults.

        Looks for pricing.json in:
        1. Custom path from settings
        2. User config directory (~/.rlm/pricing.json)
        3. Package data directory
        4. Fallback to embedded defaults
        """
        pricing = {}

        # Try custom path first
        if settings.pricing_path and settings.pricing_path.exists():
            try:
                data = json.loads(settings.pricing_path.read_text())
                return self._parse_pricing_json(data)
            except Exception as e:
                logger.warning(f"Failed to load custom pricing: {e}")

        # Try package data directory
        package_pricing = Path(__file__).parent.parent / "data" / "pricing.json"
        if package_pricing.exists():
            try:
                data = json.loads(package_pricing.read_text())
                return self._parse_pricing_json(data)
            except Exception as e:
                logger.warning(f"Failed to load package pricing: {e}")

        # Fallback to defaults
        logger.warning("Using embedded default pricing (may be outdated)")
        for model, costs in DEFAULT_PRICING.items():
            pricing[model] = PricingData(
                input_cost_per_million=costs["input_cost_per_m"],
                output_cost_per_million=costs["output_cost_per_m"],
            )

        return pricing

    def _parse_pricing_json(self, data: dict) -> dict[str, PricingData]:
        """Parse pricing JSON format."""
        pricing = {}
        models = data.get("models", data)

        for model, costs in models.items():
            if model.startswith("_"):  # Skip metadata
                continue
            pricing[model] = PricingData(
                input_cost_per_million=costs.get("input_cost_per_m", 0),
                output_cost_per_million=costs.get("output_cost_per_m", 0),
            )

        return pricing

    def get_pricing(self, model: str) -> PricingData:
        """
        Get pricing for a model.

        Falls back to a default pricing if model is unknown.

        Args:
            model: Model name

        Returns:
            PricingData for the model
        """
        if model in self.pricing:
            return self.pricing[model]

        # Try partial match (e.g., "gpt-4o-2024-01-01" -> "gpt-4o")
        for known_model in self.pricing:
            if model.startswith(known_model) or known_model.startswith(model):
                return self.pricing[known_model]

        # Unknown model - use conservative estimate
        logger.warning(f"Unknown model '{model}', using conservative pricing estimate")
        return PricingData(
            input_cost_per_million=10.0,  # Assume expensive
            output_cost_per_million=30.0,
        )

    def record_usage(
        self,
        model: str,
        input_tokens: Optional[int],
        output_tokens: Optional[int],
        check_limit: bool = True,
    ) -> float:
        """
        Record API usage and update total spent.

        Args:
            model: Model name used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            check_limit: Whether to check and enforce budget limit

        Returns:
            Cost of this usage in USD

        Raises:
            BudgetExceededError: If check_limit is True and budget is exceeded
        """
        pricing = self.get_pricing(model)
        cost = pricing.calculate_cost(input_tokens, output_tokens)

        self.total_spent += cost
        self.history.append(UsageRecord(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        ))

        logger.debug(
            f"API usage: {input_tokens} in + {output_tokens} out = ${cost:.6f} "
            f"(total: ${self.total_spent:.4f})"
        )

        if check_limit and self.total_spent > self.limit_usd:
            raise BudgetExceededError(
                message="Budget limit exceeded",
                spent=self.total_spent,
                limit=self.limit_usd,
            )

        return cost

    @property
    def remaining_budget(self) -> float:
        """Return remaining budget in USD."""
        return max(0, self.limit_usd - self.total_spent)

    @property
    def usage_percentage(self) -> float:
        """Return percentage of budget used."""
        if self.limit_usd <= 0:
            return 0.0
        return (self.total_spent / self.limit_usd) * 100

    def reset(self) -> None:
        """Reset the budget tracker."""
        self.total_spent = 0.0
        self.history.clear()

    def summary(self) -> dict:
        """Get a summary of budget usage."""
        return {
            "total_spent_usd": self.total_spent,
            "limit_usd": self.limit_usd,
            "remaining_usd": self.remaining_budget,
            "usage_percentage": self.usage_percentage,
            "total_requests": len(self.history),
            "total_input_tokens": sum(r.input_tokens for r in self.history),
            "total_output_tokens": sum(r.output_tokens for r in self.history),
        }
