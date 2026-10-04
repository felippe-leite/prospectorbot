"""Rules shared by the opportunity engine and deterministic scoring."""

from dataclasses import dataclass
from uuid import UUID

from prospector.models import (
    AnalysisStatus, Business, CheckStatus, Evidence, Opportunity,
    WebsiteAnalysis, WebsiteDiscoveryStatus,
)
from prospector.scoring.weights import ScoringConfig


APPOINTMENT_CATEGORIES = {"service.beauty.hairdresser", "service.beauty.massage", "service.beauty.spa", "service.beauty.tattoo", "healthcare.dentist"}


@dataclass
class RuleMatch:
    code: str
    evidence: list[Evidence]
    title: str | None = None
    description: str = ""
    services: tuple[str, ...] = ()


def evaluate_rules(business: Business, analysis: WebsiteAnalysis | None,
                   config: ScoringConfig) -> list[RuleMatch]:
    if analysis is not None and analysis.business_id != business.id:
        raise ValueError("Analysis belongs to a different business")
    matches = []

    def add(code, evidence, title=None, description="", services=()):
        matches.append(RuleMatch(code, evidence, title, description, services))

    # A directory not listing a URL does not prove that no website exists.
    confirmed = [item for item in business.evidence if item.code == "website_absent_confirmed"]
    if business.website_status == WebsiteDiscoveryStatus.CONFIRMED_ABSENT and confirmed:
        add("no_website", confirmed, "Presença web própria", "Ausência de website confirmada nas evidências; avaliar necessidade de um site.",
            ("Landing page", "Site institucional", "Catálogo de serviços"))
    if business.review_count is not None and business.review_count >= config.established_review_count:
        add("established_reviews", [Evidence(code="review_count", description=f"Fonte informa {business.review_count} avaliações (limiar: {config.established_review_count}); sinal de presença, não prova de orçamento.", source=business.source, observed_at=business.discovered_at)])
    website_usable = (analysis is not None and analysis.status != AnalysisStatus.FAILED
                      and analysis.status_code is not None and 200 <= analysis.status_code < 300)
    for code, field in [("whatsapp_present", "whatsapp"), ("social_present", "social_presence")]:
        supplied = [item for item in business.evidence if item.code == code]
        if website_usable and getattr(analysis, field) == CheckStatus.PRESENT:
            supplied += [item for item in analysis.evidence if item.code == field]
        if supplied:
            add(code, supplied)
    if not website_usable:
        if analysis and analysis.status_code in {404, 410}:
            add("http_error", [Evidence(code="http_status", description=f"Website informado retornou HTTP {analysis.status_code}; verificar se a URL está atualizada.", source="website_http", source_url=analysis.final_url or analysis.requested_url, observed_at=analysis.analyzed_at)],
                "Verificar endereço do website", "Uma falha HTTP nesta coleta não comprova que o negócio esteja sem website.", ("Correção de URL ou página",))
        return matches

    def html_evidence(field):
        return [item for item in analysis.evidence if item.code == field] or [Evidence(
            code=field, description=f"{field}: {getattr(analysis, field).value} no HTML analisado; escopo limitado à página inicial.",
            source="website_html", source_url=analysis.final_url or analysis.requested_url, observed_at=analysis.analyzed_at,
        )]

    if analysis.mobile_viewport == CheckStatus.ABSENT:
        add("missing_viewport", html_evidence("mobile_viewport"), "Revisar configuração mobile",
            "Viewport com width=device-width não identificado no HTML; verificar apresentação em dispositivos móveis.", ("Ajustes de responsividade",))
    if analysis.cta == CheckStatus.ABSENT:
        add("no_cta", html_evidence("cta"), "Revisar chamadas para ação",
            "CTA não identificado pelas regras no HTML inicial; verificar conteúdo renderizado antes de propor mudanças.", ("Revisão de CTA", "Otimização de conversão"))
    appointment_evidence = []
    if business.appointment_based == CheckStatus.PRESENT:
        appointment_evidence = [item for item in business.evidence if item.code == "appointment_based"]
    elif business.appointment_based == CheckStatus.UNKNOWN and business.category in APPOINTMENT_CATEGORIES:
        appointment_evidence = [Evidence(code="appointment_category_inference", description=f"Inferência: categoria {business.category} costuma operar com agendamento; confirmar com o negócio.", source=business.source, observed_at=business.discovered_at)]
    if appointment_evidence and analysis.booking == CheckStatus.ABSENT:
        add("no_booking", appointment_evidence + html_evidence("booking"), "Verificar fluxo de agendamento",
            "Não foi identificado acesso ao agendamento no HTML inicial. Pode existir em outra página ou via WhatsApp; confirmar necessidade.", ("Integração de agendamento", "Fluxo de reserva pelo WhatsApp"))
    if analysis.response_time_ms is not None and analysis.response_time_ms > config.slow_response_ms:
        add("slow_site", [Evidence(code="response_time", description=f"Resposta do HTML: {analysis.response_time_ms:.0f} ms; limiar > {config.slow_response_ms:g} ms. Medição única, sujeita à rede e ao servidor.", source="website_http", source_url=analysis.final_url or analysis.requested_url, observed_at=analysis.analyzed_at)],
            "Investigar tempo de resposta", "Resposta lenta nesta coleta; repetir medição antes de diagnosticar performance.", ("Diagnóstico de performance", "Otimização do website"))
    if (analysis.mobile_performance_score is not None and analysis.mobile_performance_source
            and analysis.mobile_performance_score < config.mobile_performance_below):
        add("poor_mobile_performance", [Evidence(code="mobile_performance", description=f"Performance mobile: {analysis.mobile_performance_score:g}/100; limiar < {config.mobile_performance_below:g}.", source=analysis.mobile_performance_source, observed_at=analysis.analyzed_at)],
            "Otimização mobile", "Métrica mobile fornecida por medição específica; analisar resultados antes da proposta.", ("Otimização de performance mobile",))
    if analysis.https == CheckStatus.ABSENT:
        add("no_https", html_evidence("https"), "Configurar HTTPS", "Endereço final usa HTTP nesta coleta.", ("Configuração de HTTPS",))
    for field, code, title in [("title_status", "missing_title", "Revisar título da página"),
                               ("meta_description_status", "missing_description", "Revisar meta description")]:
        if getattr(analysis, field) == CheckStatus.ABSENT:
            add(code, html_evidence(field), title, "Elemento não identificado no HTML inicial; avaliar relevância para busca e apresentação.", ("SEO técnico básico",))
    broken = [link for link in analysis.link_checks if link.status_code in {404, 410}]
    if broken:
        add("broken_links", [Evidence(code="broken_link", description=f"Link retornou HTTP {link.status_code}.", source="website_http", source_url=link.url, observed_at=analysis.analyzed_at) for link in broken],
            "Corrigir links indisponíveis", "Links internos amostrados retornaram 404/410; erros de conexão não contam como links quebrados.", ("Manutenção de links",))
    return matches


class OpportunityEngine:
    def __init__(self, config: ScoringConfig | None = None):
        self.config = config or ScoringConfig()

    def evaluate(self, business: Business, analysis: WebsiteAnalysis | None, scan_id: UUID) -> list[Opportunity]:
        if analysis is not None and analysis.scan_id != scan_id:
            raise ValueError("Analysis belongs to a different scan")
        return [Opportunity(business_id=business.id, scan_id=scan_id, rule_code=match.code,
                            title=match.title, description=match.description,
                            evidence=match.evidence, suggested_services=list(match.services))
                for match in evaluate_rules(business, analysis, self.config) if match.title]
