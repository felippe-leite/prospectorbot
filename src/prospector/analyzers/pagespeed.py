"""Mobile performance from Google PageSpeed Insights (Lighthouse), one request per site."""

from urllib.parse import urlencode

import httpx
from pydantic import HttpUrl

from prospector.analyzers.performance import MobilePerformance
from prospector.config import Settings
from prospector.models import Evidence


ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
SOURCE = "pagespeed_insights"


class PageSpeedError(RuntimeError):
    """A measurement failure without the API key or response body."""


class PageSpeedProvider:
    def __init__(self, settings: Settings, client: httpx.Client):
        if settings.pagespeed_api_key is None:
            raise ValueError("PageSpeed Insights requires PAGESPEED_API_KEY")
        self.key = settings.pagespeed_api_key
        self.timeout = settings.pagespeed_timeout
        self.client = client

    def measure(self, url: HttpUrl) -> MobilePerformance:
        try:
            response = self.client.get(ENDPOINT, timeout=self.timeout, params={
                "url": str(url), "strategy": "mobile", "category": "performance",
                "key": self.key.get_secret_value(),
            })
        except httpx.RequestError:
            raise PageSpeedError("PageSpeed Insights indisponível ou excedeu o tempo; performance mobile não medida.") from None
        if response.status_code == 429:
            raise PageSpeedError("Limite do PageSpeed Insights atingido (HTTP 429); performance mobile não medida.")
        if response.status_code != 200:
            raise PageSpeedError(f"PageSpeed Insights retornou HTTP {response.status_code}; performance mobile não medida.")
        try:
            score = response.json()["lighthouseResult"]["categories"]["performance"]["score"]
            value = round(float(score) * 100)
        except (ValueError, KeyError, TypeError):
            raise PageSpeedError("Resposta do PageSpeed Insights sem score de performance; performance mobile não medida.") from None
        if not 0 <= value <= 100:
            raise PageSpeedError("Score de performance fora do intervalo esperado.")
        # The public report link carries no API key.
        report = "https://pagespeed.web.dev/analysis?" + urlencode({"url": str(url), "form_factor": "mobile"})
        return MobilePerformance(score=value, evidence=Evidence(
            code="mobile_performance", source=SOURCE, source_url=report,
            description=f"Lighthouse mobile (PageSpeed Insights): performance {value}/100. Uma medição em ambiente simulado.",
        ))
