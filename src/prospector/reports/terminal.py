"""Human-readable ranking and evidence reports; no automated contact."""

import json
from pathlib import Path
import unicodedata
from uuid import UUID

from prospector.database.repository import Repository
from prospector.models import Scan, Score


ATTRIBUTION = "Dados: Geoapify (https://www.geoapify.com/) | © OpenStreetMap contributors (https://www.openstreetmap.org/copyright)"


def safe_text(value: object) -> str:
    return " ".join("".join(char for char in str(value) if not unicodedata.category(char).startswith("C")).split())


def ranking(repo: Repository, scan: Scan) -> str:
    scores = repo.list_scores(scan.id)
    lines = ["ProspectorBot", f"Scan: {scan.id}", f"Busca: {safe_text(scan.query)} | Região: {safe_text(scan.location)}",
             f"{len(scores)} negócios avaliados", ""]
    for index, score in enumerate(scores, 1):
        business = repo.get_business(score.business_id, scan.id)
        lines.append(f"{index:>2}. {safe_text(business.name):<36} {score.value:>3}  {score.classification.value}")
    if not scores:
        lines.append("Nenhum resultado encontrado nesta fonte para a busca.")
    lines.extend(["", "O score prioriza revisão humana; não comprova necessidade ou intenção de contratar.", ATTRIBUTION])
    return "\n".join(lines)


def detail(repo: Repository, scan_id: UUID, score: Score) -> str:
    business = repo.get_business(score.business_id, scan_id)
    lines = [safe_text(business.name), f"Business ID: {business.id}", f"Scan: {scan_id}",
             f"Prospector Score: {score.value}/100", f"Classification: {score.classification.value}",
             f"Scoring version: {score.scoring_version}",
             f"Website: {business.website or business.website_status.value}", "", "Evidence / pontuação:"]
    for contribution in score.contributions:
        lines.append(f"+{contribution.points} — {contribution.rule_code}")
        lines.extend(f"  - {safe_text(item.description)} [fonte: {safe_text(item.source)}]" for item in contribution.evidence)
    if not score.contributions:
        lines.append("Nenhum critério de pontuação comprovado pelas regras.")
    lines.extend(["", "Outras evidências da descoberta:"])
    lines.extend(f"- {safe_text(item.description)}" for item in business.evidence)
    for analysis in repo.list_analyses(business.id, scan_id):
        lines.extend(["", f"Website analysis: {analysis.status.value}"])
        lines.extend(f"- {safe_text(item.description)}" for item in analysis.evidence)
        lines.extend(f"- Verificação inconclusiva: {safe_text(error)}" for error in analysis.errors)
        lines.extend(f"- Link não verificado: {link.url}: {safe_text(link.error)}" for link in analysis.link_checks if link.error)
    opportunities = repo.list_opportunities(business.id, scan_id)
    lines.extend(["", "Potential opportunities:"])
    for opportunity in opportunities:
        lines.extend([f"- {safe_text(opportunity.title)}", f"  {safe_text(opportunity.description)}",
                      f"  Serviços: {', '.join(safe_text(item) for item in opportunity.suggested_services)}"])
    if not opportunities:
        lines.append("Nenhuma oportunidade relevante identificada pelas regras disponíveis.")
    lines.extend(["", "Validar as evidências e inferências antes de abordar o negócio.", ATTRIBUTION])
    return "\n".join(lines)


def export_json(repo: Repository, scan: Scan, path: Path) -> None:
    leads = []
    for score in repo.list_scores(scan.id):
        leads.append({
            "business": repo.get_business(score.business_id, scan.id).model_dump(mode="json"),
            "score": score.model_dump(mode="json"),
            "analyses": [item.model_dump(mode="json") for item in repo.list_analyses(score.business_id, scan.id)],
            "opportunities": [item.model_dump(mode="json") for item in repo.list_opportunities(score.business_id, scan.id)],
        })
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"scan": scan.model_dump(mode="json"), "attribution": ATTRIBUTION,
                                "leads": leads}, ensure_ascii=False, indent=2), encoding="utf-8")
