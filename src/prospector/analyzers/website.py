"""Homepage HTML signals; absence is scoped to HTML, never visual quality."""

import re
from typing import Protocol
from uuid import UUID
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from prospector.analyzers.fetcher import FetchError, PublicFetcher
from prospector.analyzers.pagespeed import PageSpeedError
from prospector.analyzers.performance import MobilePerformanceProvider
from prospector.enrichment.normalization import (
    SOCIAL_HOSTS, WHATSAPP_HOSTS, host_matches, normalize_website, search_key,
)
from prospector.models import (
    AnalysisStatus, Business, CheckStatus, Evidence, LinkCheck, WebsiteAnalysis,
)


class WebsiteAnalyzer(Protocol):
    def analyze(self, business: Business, scan_id: UUID) -> WebsiteAnalysis: ...


CTA_PATTERN = re.compile(r"\b(agend\w*|reserv\w*|orcamento|solicite|contrate|compre|comprar|fale|contato|contact|book|schedule|quote|buy)\b")
BOOKING_PATTERN = re.compile(r"\b(agend\w*|reserv\w*|booking|book|schedule|appointment)\b")
BOOKING_HOSTS = {"calendly.com", "booksy.com", "trinks.com", "fresha.com", "simplybook.me", "setmore.com"}
# Markers only present on challenge interstitials (e.g. Cloudflare), not on regular pages.
CHALLENGE_MARKERS = re.compile(r"cf-chl-|cf_chl_opt", re.I)
CHALLENGE_TEXT = re.compile(r"captcha|verify you are human|are you a robot|just a moment|access denied|attention required", re.I)
CHALLENGE_MAX_TEXT = 500


def looks_like_challenge(html: str) -> bool:
    """Detect challenge screens without flagging regular pages that embed reCAPTCHA/hCaptcha."""
    if CHALLENGE_MARKERS.search(html):
        return True
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    for node in soup.select("script, style, template, noscript"):
        node.decompose()
    # Only visible text counts: widget scripts and class names (g-recaptcha) are ignored.
    text = soup.get_text(" ", strip=True)
    return bool(CHALLENGE_TEXT.search(title) or (len(text) < CHALLENGE_MAX_TEXT and CHALLENGE_TEXT.search(text)))


def parse_html(analysis: WebsiteAnalysis, html: str) -> WebsiteAnalysis:
    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select("script, style, template, noscript, [hidden], [aria-hidden='true']"):
        node.decompose()
    # Sparse content can be a JS app or an interstitial: no negative HTML conclusions.
    visible_text = soup.get_text(" ", strip=True)
    html_complete = bool(soup.html and soup.body and len(visible_text) >= 80)
    missing = CheckStatus.ABSENT if html_complete else CheckStatus.UNKNOWN
    url = str(analysis.final_url or analysis.requested_url)

    def observed(code: str, description: str) -> None:
        analysis.evidence.append(Evidence(code=code, description=description, source="website_html", source_url=url,
                                          observed_at=analysis.analyzed_at))

    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    analysis.title = title or None
    analysis.title_status = CheckStatus.PRESENT if title else missing
    meta = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    description = str(meta.get("content", "")).strip() if meta else ""
    analysis.meta_description = description or None
    analysis.meta_description_status = CheckStatus.PRESENT if description else missing
    viewport = soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)})
    has_viewport = bool(viewport and "width=device-width" in re.sub(r"\s", "", str(viewport.get("content", "")).lower()))
    analysis.mobile_viewport = CheckStatus.PRESENT if has_viewport else missing
    analysis.headings = [text for node in soup.find_all(["h1", "h2"]) if (text := node.get_text(" ", strip=True))]
    analysis.headings_status = CheckStatus.PRESENT if analysis.headings else missing
    links = [str(node.get("href", "")) for node in soup.find_all("a", href=True)]
    normalized = [item for href in links if (item := normalize_website(urljoin(url, href)))]
    analysis.social_links = list(dict.fromkeys(item for item in normalized if host_matches(item.host, SOCIAL_HOSTS)))
    analysis.social_presence = CheckStatus.PRESENT if analysis.social_links else missing
    analysis.phone = CheckStatus.PRESENT if any(href.lower().startswith("tel:") for href in links) or re.search(
        r"(?:\+55\s*)?\(?\d{2}\)?[\s.-]*\d{4,5}[\s.-]+\d{4}\b", visible_text
    ) else missing
    analysis.whatsapp_links = list(dict.fromkeys(item for item in normalized if host_matches(item.host, WHATSAPP_HOSTS)))
    analysis.whatsapp = CheckStatus.PRESENT if analysis.whatsapp_links else missing
    controls = soup.find_all(["a", "button", "input"])
    analysis.cta = CheckStatus.PRESENT if any(CTA_PATTERN.search(search_key(
        node.get_text(" ", strip=True) + " " + str(node.get("aria-label", "")) + " " + str(node.get("value", ""))
    )) for node in controls) else missing
    forms = soup.find_all("form")
    contact_forms = [form for form in forms if form.find("textarea") or form.find("input", attrs={"type": re.compile("^(email|tel)$", re.I)})]
    analysis.contact_form = CheckStatus.PRESENT if contact_forms else missing
    booking = any(host_matches(item.host, BOOKING_HOSTS) for item in normalized) or any(
        BOOKING_PATTERN.search(search_key(href + " " + node.get_text(" ", strip=True)))
        for node in soup.find_all("a", href=True) if (href := str(node.get("href", "")))
    ) or any(form.find("input", attrs={"type": re.compile("^(date|datetime-local)$", re.I)}) for form in forms)
    analysis.booking = CheckStatus.PRESENT if booking else missing
    for field in ["title_status", "meta_description_status", "mobile_viewport", "headings_status", "phone", "whatsapp", "cta", "contact_form", "booking", "social_presence"]:
        status = getattr(analysis, field)
        observed(field, f"{field}: {status.value} no HTML da página inicial. Não confirma conteúdo de outras páginas ou JavaScript.")
    if not html_complete:
        analysis.status = AnalysisStatus.PARTIAL
        analysis.errors.append("HTML escasso/incompleto; sinais ausentes permanecem desconhecidos.")
    return analysis


class HtmlWebsiteAnalyzer:
    def __init__(self, fetcher: PublicFetcher, max_links: int = 5,
                 performance: MobilePerformanceProvider | None = None):
        self.fetcher = fetcher
        self.max_links = max_links
        self.performance = performance

    def analyze(self, business: Business, scan_id: UUID) -> WebsiteAnalysis:
        if business.website is None:
            raise ValueError("Website analysis requires a website URL")
        analysis = WebsiteAnalysis(business_id=business.id, scan_id=scan_id,
                                   requested_url=business.website, status="failed")
        try:
            page = self.fetcher.fetch(str(business.website))
        except FetchError as exc:
            analysis.errors.append(str(exc))
            return analysis
        analysis.final_url = HttpUrl(page.url)
        analysis.status_code = page.status_code
        analysis.redirect_chain = [HttpUrl(url) for url in page.redirects]
        analysis.response_time_ms = page.elapsed_ms
        analysis.https = CheckStatus.PRESENT if urlsplit(page.url).scheme == "https" else CheckStatus.ABSENT
        analysis.evidence.extend([
            Evidence(code="http_status", description=f"Página inicial retornou HTTP {page.status_code}.", source="website_http", source_url=page.url),
            Evidence(code="response_time", description=f"HTML e redirects recebidos em {page.elapsed_ms:.0f} ms; uma medição, não Lighthouse.", source="website_http", source_url=page.url),
            Evidence(code="https", description=f"HTTPS: {analysis.https.value} no endereço final.", source="website_http", source_url=page.url),
        ])
        if not 200 <= page.status_code < 300:
            analysis.errors.append(f"HTTP {page.status_code}; sinais de conteúdo não analisados.")
            return analysis
        if "text/html" not in page.content_type.lower():
            analysis.status = AnalysisStatus.PARTIAL
            analysis.errors.append("Resposta não identificada como HTML.")
            return analysis
        # Common challenge/consent screens must not become opportunities.
        if looks_like_challenge(page.text):
            analysis.status = AnalysisStatus.PARTIAL
            analysis.errors.append("Possível CAPTCHA/bloqueio; sem tentar contornar ou analisar sinais ausentes.")
            return analysis
        analysis.status = AnalysisStatus.COMPLETED
        parse_html(analysis, page.text)
        self._measure_performance(analysis)
        soup = BeautifulSoup(page.text, "html.parser")
        candidates = []
        for anchor in soup.find_all("a", href=True):
            href = str(anchor["href"])
            if href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            url = normalize_website(urljoin(page.url, href))
            # Do not follow social/WhatsApp links or crawl external sites.
            if url and urlsplit(str(url)).netloc == urlsplit(page.url).netloc and str(url) != page.url:
                if url not in candidates:
                    candidates.append(url)
        for url in candidates[:self.max_links]:
            try:
                linked = self.fetcher.fetch(str(url))
                analysis.link_checks.append(LinkCheck(url=url, status_code=linked.status_code))
            except FetchError as exc:
                analysis.link_checks.append(LinkCheck(url=url, error=str(exc)))
                analysis.status = AnalysisStatus.PARTIAL
        return analysis

    def _measure_performance(self, analysis: WebsiteAnalysis) -> None:
        # Only reached after robots.txt allowed our own fetch of this page.
        if self.performance is None:
            return
        try:
            result = self.performance.measure(analysis.final_url or analysis.requested_url)
        except PageSpeedError as exc:
            analysis.errors.append(str(exc))
            return
        if result is not None:
            analysis.mobile_performance_score = result.score
            analysis.mobile_performance_source = result.evidence.source
            analysis.evidence.append(result.evidence)
