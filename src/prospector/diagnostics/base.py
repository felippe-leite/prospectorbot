"""Future evidence-only diagnosis contract. No LLM implementation or dependency."""

from typing import Protocol

from pydantic import Field

from prospector.models import DomainModel, Evidence, NonEmptyText, Opportunity


class Diagnosis(DomainModel):
    facts: list[Evidence] = Field(default_factory=list)
    inferences: list[NonEmptyText] = Field(default_factory=list)
    suggested_services: list[NonEmptyText] = Field(default_factory=list)
    relevant_opportunity: bool


class EvidenceDiagnostician(Protocol):
    """Implementations must ground facts in supplied evidence, label inferences,
    and may conclude no relevant opportunity. They cannot change the score.
    """

    def diagnose(self, evidence: list[Evidence], opportunities: list[Opportunity]) -> Diagnosis: ...
