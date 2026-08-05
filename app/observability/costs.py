"""Provider-neutral token accounting with explicitly configured prices."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0

    def __post_init__(self) -> None:
        if min(self.input_tokens, self.output_tokens, self.cached_input_tokens) < 0:
            raise ValueError("token counts must be non-negative")
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached input tokens cannot exceed input tokens")

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """USD per one million tokens; values come from deployment configuration."""

    input_per_million: Decimal
    output_per_million: Decimal
    cached_input_per_million: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if (
            min(
                self.input_per_million,
                self.output_per_million,
                self.cached_input_per_million,
            )
            < 0
        ):
            raise ValueError("token prices must be non-negative")


@dataclass(frozen=True, slots=True)
class UsageCost:
    usage: TokenUsage
    estimated_cost_usd: Decimal


def estimate_usage_cost(usage: TokenUsage, pricing: ModelPricing) -> UsageCost:
    """Estimate cost without embedding volatile provider pricing in source code."""

    million = Decimal(1_000_000)
    uncached = usage.input_tokens - usage.cached_input_tokens
    cost = (
        Decimal(uncached) * pricing.input_per_million
        + Decimal(usage.cached_input_tokens) * pricing.cached_input_per_million
        + Decimal(usage.output_tokens) * pricing.output_per_million
    ) / million
    return UsageCost(usage=usage, estimated_cost_usd=cost)
