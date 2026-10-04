"""Versioned, configurable scoring weights and objective thresholds."""

from pathlib import Path
import hashlib

from pydantic import BaseModel, ConfigDict, Field


class Weights(BaseModel):
    model_config = ConfigDict(extra="forbid")
    no_website: int = Field(default=25, ge=0, le=100)
    poor_mobile_performance: int = Field(default=20, ge=0, le=100)
    no_cta: int = Field(default=10, ge=0, le=100)
    no_booking: int = Field(default=15, ge=0, le=100)
    whatsapp_present: int = Field(default=5, ge=0, le=100)
    established_reviews: int = Field(default=10, ge=0, le=100)
    social_present: int = Field(default=5, ge=0, le=100)
    slow_site: int = Field(default=10, ge=0, le=100)
    # Viewport is an independent technical signal, not mobile performance.
    missing_viewport: int = Field(default=10, ge=0, le=100)


class ScoringConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    weights: Weights = Field(default_factory=Weights)
    slow_response_ms: float = Field(default=3000, gt=0, allow_inf_nan=False)
    mobile_performance_below: float = Field(default=50, ge=0, le=100, allow_inf_nan=False)
    established_review_count: int = Field(default=50, ge=1)

    @classmethod
    def load(cls, path: Path | None) -> "ScoringConfig":
        return cls.model_validate_json(path.read_text(encoding="utf-8")) if path else cls()

    @property
    def version(self) -> str:
        digest = hashlib.sha256(self.model_dump_json().encode()).hexdigest()[:12]
        return f"0.1-{digest}"
