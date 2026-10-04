"""Deterministic rules: configurable weights, transparent contributions."""

from uuid import UUID

from prospector.models import Business, Score, ScoreContribution, WebsiteAnalysis
from prospector.opportunities.rules import evaluate_rules
from prospector.scoring.weights import ScoringConfig


class ScoreEngine:
    def __init__(self, config: ScoringConfig | None = None):
        self.config = config or ScoringConfig()

    def calculate(self, business: Business, analysis: WebsiteAnalysis | None, scan_id: UUID) -> Score:
        if analysis is not None and analysis.scan_id != scan_id:
            raise ValueError("Analysis belongs to a different scan")
        weights = self.config.weights.model_dump()
        contributions = [ScoreContribution(rule_code=match.code, points=weights[match.code], evidence=match.evidence)
                         for match in evaluate_rules(business, analysis, self.config)
                         if weights.get(match.code, 0) > 0]
        return Score(business_id=business.id, scan_id=scan_id,
                     scoring_version=self.config.version, contributions=contributions)
