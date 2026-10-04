"""Optional future mobile measurement contract, independent from HTML checks."""

from typing import Protocol

from pydantic import Field, HttpUrl

from prospector.models import DomainModel, Evidence


class MobilePerformance(DomainModel):
    score: float = Field(ge=0, le=100, allow_inf_nan=False)
    evidence: Evidence


class MobilePerformanceProvider(Protocol):
    def measure(self, url: HttpUrl) -> MobilePerformance | None: ...
