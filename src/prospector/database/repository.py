"""Persistence operations; callers own the transaction via session_scope."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from prospector import models as domain
from prospector.database import models as tables


@dataclass
class RankedLead:
    """A scored business as captured by one scan."""

    scan: domain.Scan
    business: domain.Business
    score: domain.Score
    opportunities: list[domain.Opportunity]


class Repository:
    def __init__(self, session: Session):
        self.session = session

    def save_scan(self, scan: domain.Scan) -> domain.Scan:
        row = self.session.get(tables.Scan, str(scan.id))
        payload = scan.model_dump(mode="json")
        if row is None:
            self.session.add(tables.Scan(
                id=str(scan.id), created_at=scan.created_at.isoformat(), payload=payload,
            ))
        else:
            row.payload = payload
        self.session.flush()
        return scan

    def get_scan(self, scan_id: UUID) -> domain.Scan | None:
        row = self.session.get(tables.Scan, str(scan_id))
        return domain.Scan.model_validate(row.payload) if row else None

    def list_scans(self) -> list[domain.Scan]:
        rows = self.session.scalars(select(tables.Scan).order_by(
            tables.Scan.created_at.desc(), tables.Scan.id,
        ))
        return [domain.Scan.model_validate(row.payload) for row in rows]

    def save_business(self, business: domain.Business, scan_id: UUID) -> domain.Business:
        """Return the canonical ID; use it for this scan's analysis and score.

        A reliable source ID enables deduplication. A missing source ID never
        triggers matching by name, address, or phone. Earlier snapshots are
        preserved; registering the same business twice in one scan is idempotent.
        """
        if self.session.get(tables.Scan, str(scan_id)) is None:
            raise ValueError("Save the scan before registering a business")

        existing_id = self.session.get(tables.Business, str(business.id))
        if existing_id is not None and (
            existing_id.source != business.source or existing_id.source_id != business.source_id
        ):
            raise ValueError("A business ID cannot be reused with a different source identity")

        payload = business.model_dump(mode="json")
        statement = insert(tables.Business).values(
            id=str(business.id), source=business.source, source_id=business.source_id,
            name=business.name, payload=payload,
        )
        # Atomic conflict handling also protects the source identity at DB level.
        self.session.execute(statement.on_conflict_do_nothing())
        if business.source_id is not None:
            row = self.session.scalar(select(tables.Business).where(
                tables.Business.source == business.source,
                tables.Business.source_id == business.source_id,
            ))
        else:
            row = self.session.get(tables.Business, str(business.id))
        if row is None:
            raise ValueError("Could not resolve the business identity")
        canonical = domain.Business.model_validate({**payload, "id": row.id})
        key = (str(scan_id), row.id)
        snapshot = self.session.get(tables.ScanBusiness, key)
        if snapshot is not None:
            return domain.Business.model_validate(snapshot.payload)

        row.name = canonical.name
        row.payload = canonical.model_dump(mode="json")
        self.session.add(tables.ScanBusiness(
            scan_id=str(scan_id), business_id=row.id, payload=row.payload,
        ))
        self.session.flush()
        return canonical

    def get_business(self, business_id: UUID, scan_id: UUID | None = None) -> domain.Business | None:
        if scan_id is None:
            row = self.session.get(tables.Business, str(business_id))
        else:
            row = self.session.get(tables.ScanBusiness, (str(scan_id), str(business_id)))
        return domain.Business.model_validate(row.payload) if row else None

    def list_businesses(self, scan_id: UUID | None = None) -> list[domain.Business]:
        if scan_id is None:
            rows = self.session.scalars(select(tables.Business).order_by(
                tables.Business.name, tables.Business.id,
            ))
        else:
            rows = self.session.scalars(select(tables.ScanBusiness).where(
                tables.ScanBusiness.scan_id == str(scan_id),
            ).order_by(tables.ScanBusiness.business_id))
        return [domain.Business.model_validate(row.payload) for row in rows]

    def _require_membership(self, business_id: UUID, scan_id: UUID) -> None:
        if self.session.get(tables.ScanBusiness, (str(scan_id), str(business_id))) is None:
            raise ValueError("Business must be registered in this scan")

    def save_analysis(self, analysis: domain.WebsiteAnalysis) -> domain.WebsiteAnalysis:
        self._require_membership(analysis.business_id, analysis.scan_id)
        row = self.session.get(tables.WebsiteAnalysis, str(analysis.id))
        payload = analysis.model_dump(mode="json")
        if row is not None:
            if row.payload != payload:
                raise ValueError("An existing analysis is immutable; use a new analysis ID")
            return analysis
        self.session.add(tables.WebsiteAnalysis(
            id=str(analysis.id), scan_id=str(analysis.scan_id),
            business_id=str(analysis.business_id), payload=payload,
        ))
        self.session.flush()
        return analysis

    def list_analyses(self, business_id: UUID, scan_id: UUID | None = None) -> list[domain.WebsiteAnalysis]:
        statement = select(tables.WebsiteAnalysis).where(
            tables.WebsiteAnalysis.business_id == str(business_id),
        )
        if scan_id is not None:
            statement = statement.where(tables.WebsiteAnalysis.scan_id == str(scan_id))
        results = [domain.WebsiteAnalysis.model_validate(row.payload)
                   for row in self.session.scalars(statement)]
        return sorted(results, key=lambda item: (item.analyzed_at, str(item.id)))

    def save_opportunity(self, opportunity: domain.Opportunity) -> domain.Opportunity:
        self._require_membership(opportunity.business_id, opportunity.scan_id)
        payload = opportunity.model_dump(mode="json")
        row = self.session.get(tables.Opportunity, str(opportunity.id))
        if row is not None:
            if row.payload != payload:
                raise ValueError("An existing opportunity is immutable")
            return opportunity
        self.session.add(tables.Opportunity(
            id=str(opportunity.id), scan_id=str(opportunity.scan_id),
            business_id=str(opportunity.business_id), rule_code=opportunity.rule_code,
            payload=payload,
        ))
        self.session.flush()
        return opportunity

    def list_opportunities(self, business_id: UUID, scan_id: UUID | None = None) -> list[domain.Opportunity]:
        statement = select(tables.Opportunity).where(
            tables.Opportunity.business_id == str(business_id),
        )
        if scan_id is not None:
            statement = statement.where(tables.Opportunity.scan_id == str(scan_id))
        return [domain.Opportunity.model_validate(row.payload) for row in
                self.session.scalars(statement.order_by(tables.Opportunity.scan_id, tables.Opportunity.rule_code))]

    def save_score(self, score: domain.Score) -> domain.Score:
        self._require_membership(score.business_id, score.scan_id)
        payload = score.model_dump(mode="json", exclude={"value", "classification"})
        row = self.session.get(tables.Score, (str(score.scan_id), str(score.business_id)))
        if row is not None:
            if row.payload != payload:
                raise ValueError("A score already exists for this scan; use a new scan")
            return score
        self.session.add(tables.Score(
            scan_id=str(score.scan_id), business_id=str(score.business_id),
            value=score.value, payload=payload,
        ))
        self.session.flush()
        return score

    def get_score(self, business_id: UUID, scan_id: UUID) -> domain.Score | None:
        row = self.session.get(tables.Score, (str(scan_id), str(business_id)))
        return domain.Score.model_validate(row.payload) if row else None

    def list_scores(self, scan_id: UUID) -> list[domain.Score]:
        """Return a scan's ranking, including a stable tie breaker."""
        rows = self.session.scalars(select(tables.Score).where(
            tables.Score.scan_id == str(scan_id),
        ).order_by(tables.Score.value.desc(), tables.Score.business_id))
        return [domain.Score.model_validate(row.payload) for row in rows]

    def list_ranked(self, scan_id: UUID | None = None, business_id: UUID | None = None) -> list[RankedLead]:
        """Scored snapshots, newest scan first and highest score first within a scan."""
        statement = (select(tables.Score, tables.ScanBusiness, tables.Scan)
                     .join(tables.ScanBusiness, and_(tables.ScanBusiness.scan_id == tables.Score.scan_id,
                                                     tables.ScanBusiness.business_id == tables.Score.business_id))
                     .join(tables.Scan, tables.Scan.id == tables.Score.scan_id)
                     .order_by(tables.Scan.created_at.desc(), tables.Score.value.desc(), tables.Score.business_id))
        opportunities = select(tables.Opportunity).order_by(tables.Opportunity.rule_code)
        if scan_id is not None:
            statement = statement.where(tables.Score.scan_id == str(scan_id))
            opportunities = opportunities.where(tables.Opportunity.scan_id == str(scan_id))
        if business_id is not None:
            statement = statement.where(tables.Score.business_id == str(business_id))
            opportunities = opportunities.where(tables.Opportunity.business_id == str(business_id))
        grouped: dict[tuple[str, str], list[domain.Opportunity]] = {}
        for row in self.session.scalars(opportunities):
            grouped.setdefault((row.scan_id, row.business_id), []).append(domain.Opportunity.model_validate(row.payload))
        scans: dict[str, domain.Scan] = {}
        results = []
        for score, snapshot, scan in self.session.execute(statement):
            if scan.id not in scans:
                scans[scan.id] = domain.Scan.model_validate(scan.payload)
            results.append(RankedLead(
                scan=scans[scan.id], business=domain.Business.model_validate(snapshot.payload),
                score=domain.Score.model_validate(score.payload),
                opportunities=grouped.get((score.scan_id, score.business_id), []),
            ))
        return results

    def scan_counts(self, gold_threshold: int = 85) -> dict[UUID, tuple[int, int]]:
        """Scored businesses and Gold Nuggets per scan."""
        statement = select(tables.Score.scan_id, func.count(),
                           func.sum(case((tables.Score.value >= gold_threshold, 1), else_=0))
                           ).group_by(tables.Score.scan_id)
        return {UUID(scan_id): (total, gold or 0) for scan_id, total, gold in self.session.execute(statement)}

    def get_tracking(self, business_id: UUID) -> domain.LeadTracking:
        row = self.session.get(tables.LeadTracking, str(business_id))
        return domain.LeadTracking.model_validate(row.payload) if row else domain.LeadTracking(business_id=business_id)

    def list_tracking(self) -> dict[UUID, domain.LeadTracking]:
        return {UUID(row.business_id): domain.LeadTracking.model_validate(row.payload)
                for row in self.session.scalars(select(tables.LeadTracking))}

    def save_tracking(self, tracking: domain.LeadTracking) -> domain.LeadTracking:
        if self.session.get(tables.Business, str(tracking.business_id)) is None:
            raise ValueError("Tracking requires a known business")
        payload = tracking.model_dump(mode="json")
        row = self.session.get(tables.LeadTracking, str(tracking.business_id))
        if row is None:
            self.session.add(tables.LeadTracking(business_id=str(tracking.business_id), payload=payload))
        else:
            row.payload = payload
        self.session.flush()
        return tracking
