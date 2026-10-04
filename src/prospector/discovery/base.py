"""Provider contract; the application does not depend on a vendor."""

from typing import Protocol

from prospector.models import Business


class DiscoveryError(RuntimeError):
    """An actionable discovery error without API credentials or response bodies."""


class BusinessProvider(Protocol):
    def search(self, query: str, location: str, limit: int) -> list[Business]: ...
