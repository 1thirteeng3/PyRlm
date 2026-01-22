# Budget Management

The `BudgetManager` tracks API costs and enforces spending limits.

## Why Budget Management?

LLM APIs charge per token. Without limits, a runaway loop could:

- Consume thousands of tokens
- Cost hundreds of dollars
- Drain your API budget

## Basic Usage

```python
from rlm.utils import BudgetManager

budget = BudgetManager(limit_usd=5.0)

# Record usage
cost = budget.record_usage(
    model="gpt-4o",
    input_tokens=1000,
    output_tokens=500
)

print(f"This call cost: ${cost:.4f}")
print(f"Total spent: ${budget.total_spent:.4f}")
print(f"Remaining: ${budget.remaining_budget:.4f}")
```

## Budget Enforcement

When the limit is exceeded:

```python
from rlm.core.exceptions import BudgetExceededError

try:
    budget.record_usage("gpt-4o", 100000, 50000)
except BudgetExceededError as e:
    print(f"Budget exceeded: ${e.spent:.2f} / ${e.limit:.2f}")
```

## Usage Summary

```python
summary = budget.summary()
print(summary)
# {
#     'total_spent_usd': 0.0125,
#     'limit_usd': 5.0,
#     'remaining_usd': 4.9875,
#     'usage_percentage': 0.25,
#     'total_requests': 3,
#     'total_input_tokens': 5000,
#     'total_output_tokens': 2000
# }
```

## Pricing Data

Pricing is loaded from `pricing.json`:

```json
{
  "models": {
    "gpt-4o": {
      "input_cost_per_m": 5.00,
      "output_cost_per_m": 15.00
    }
  }
}
```

Costs are in USD per million tokens.

### Custom Pricing

```bash
RLM_PRICING_PATH=/path/to/custom/pricing.json
```

## Configuration

```bash
RLM_COST_LIMIT_USD=5.0   # Default budget limit
```

## With Orchestrator

The Orchestrator automatically tracks costs:

```python
from rlm import Orchestrator

orchestrator = Orchestrator()
result = orchestrator.run("Complex query...")

print(f"Cost: ${result.budget_summary['total_spent_usd']:.4f}")
print(f"Tokens: {result.budget_summary['total_input_tokens'] + result.budget_summary['total_output_tokens']}")
```

## Resetting Budget

```python
budget.reset()
print(budget.total_spent)  # 0.0
```
