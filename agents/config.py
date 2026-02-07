"""Agent and model configuration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ModelConfig:
    """Configuration for an OpenRouter model."""

    id: str  # OpenRouter model ID
    label: str  # Human-readable short name
    tier: str  # "weak", "medium", "strong"
    max_tokens: int = 4096
    temperature: float = 0.2


# Models chosen to show clear capability differences:
# - Weak:   small model, limited reasoning
# - Medium: solid open-source model
# - Strong: top-tier commercial model
MODELS: dict[str, ModelConfig] = {
    "weak": ModelConfig(
        id="google/gemma-2-9b-it",
        label="Gemma 2 9B",
        tier="weak",
        temperature=0.3,
    ),
    "medium": ModelConfig(
        id="meta-llama/llama-3.3-70b-instruct",
        label="Llama 3.3 70B",
        tier="medium",
        temperature=0.2,
    ),
    "strong": ModelConfig(
        id="anthropic/claude-sonnet-4",
        label="Claude Sonnet",
        tier="strong",
        temperature=0.1,
    ),
}


def get_model(tier: str) -> ModelConfig:
    """Get model config by tier name."""
    if tier not in MODELS:
        raise ValueError(f"Unknown model tier: {tier}. Choose from: {list(MODELS.keys())}")
    return MODELS[tier]


def list_models() -> list[ModelConfig]:
    """Return all configured models."""
    return list(MODELS.values())
