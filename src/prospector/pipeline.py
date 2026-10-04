"""Production discovery and analysis components, shared by the CLI and the API."""

from collections.abc import Iterator
from contextlib import contextmanager

import httpx

from prospector.analyzers.fetcher import PublicFetcher, USER_AGENT
from prospector.analyzers.pagespeed import PageSpeedProvider
from prospector.analyzers.website import HtmlWebsiteAnalyzer
from prospector.config import Settings
from prospector.discovery.geoapify import GeoapifyProvider


@contextmanager
def scan_pipeline(settings: Settings) -> Iterator[tuple[GeoapifyProvider, HtmlWebsiteAnalyzer]]:
    # Separate clients keep API credentials away from business websites.
    with httpx.Client(trust_env=False, headers={"User-Agent": USER_AGENT}) as provider_client, \
            httpx.Client(trust_env=False) as website_client, \
            httpx.Client(trust_env=False, headers={"User-Agent": USER_AGENT}) as pagespeed_client:
        performance = PageSpeedProvider(settings, pagespeed_client) if settings.pagespeed_api_key else None
        yield (GeoapifyProvider(settings, provider_client),
               HtmlWebsiteAnalyzer(PublicFetcher(website_client, settings), settings.max_links, performance))
