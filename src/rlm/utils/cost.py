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
    "claude-3-opus": {"input_cost_per_m": 15.00, "output_cost_per_m": 75.00},
    "claude-3-sonnet": {"input_cost_per_m": 3.00, "output_cost_per_m": 15.00},
    "claude-3-sonnet-20240229": {"input_cost_per_m": 3.00, "output_cost_per_m": 15.00},
    "gemini-1.5-pro": {"input_cost_per_m": 3.50, "output_cost_per_m": 10.50},
}


@dataclass
class PricingData:
    """Pricing information for a model."""

    input_cost_per_million: float
    output_cost_per_million: float

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate the cost for a given number of tokens.

        Args:
            input_tokens: Number of input/prompt tokens
            output_tokens: Number of output/completion tokens

        Returns:
            Total cost in USD
        """
        input_cost = (input_tokens / 1_000_000) * self.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * self.output_cost_per_million
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
        input_tokens: int,
        output_tokens: int,
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
