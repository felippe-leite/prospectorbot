"""Geoapify Places and Place Details adapter with bounded sequential requests."""

import re
import time

import httpx

from prospector.config import Settings
from prospector.discovery.base import DiscoveryError
from prospector.discovery.categories import CATEGORIES
from prospector.enrichment.normalization import (
    SOCIAL_HOSTS, WHATSAPP_HOSTS, host_matches, normalize_phone, normalize_text,
    normalize_website, search_key,
)
from prospector.models import Business, Evidence, WebsiteDiscoveryStatus


def category_for(query: str) -> str:
    key = search_key(query)
    niche = " ".join(re.sub(r"[-–]", " ", key).split())
    if niche in CATEGORIES:
        return CATEGORIES[niche]
    # Advanced users may use a documented Geoapify category directly.
    if re.fullmatch(r"[a-z_]+(?:\.[a-z_]+)+", key):
        return key
    raise DiscoveryError("Nicho não reconhecido. Use 'prospector categories' ou uma categoria Geoapify.")


LOCATION_COUNTRY = "br"
LOCATION_CACHE_SIZE = 500


class GeoapifyProvider:
    def __init__(self, settings: Settings, client: httpx.Client):
        self.settings = settings
        self.client = client
        self._last_request = 0.0
        self._locations: dict[str, list[str]] = {}

    def suggest_locations(self, text: str, limit: int = 6) -> list[str]:
        """City/region names that discovery geocodes back to the same place."""
        key = search_key(text)
        if key not in self._locations:
            payload = self._get("v1/geocode/autocomplete", text=text, lang="pt", limit=limit, format="json",
                                filter=f"countrycode:{LOCATION_COUNTRY}")
            labels = []
            for item in payload.get("results", []):
                parts = [part.strip() for part in str(item.get("formatted") or "").split(",") if part.strip()]
                if parts and parts[-1] == item.get("country"):
                    parts.pop()  # "Campinas, SP, Brasil" -> "Campinas, SP"
                if parts and item.get("result_type") in {"city", "district", "suburb", "county", "postcode"}:
                    labels.append(", ".join(parts))
            if len(self._locations) >= LOCATION_CACHE_SIZE:
                self._locations.clear()
            self._locations[key] = list(dict.fromkeys(labels))
        return self._locations[key]

    def _get(self, endpoint: str, **params) -> dict:
        key = self.settings.geoapify_api_key
        if key is None:
            raise DiscoveryError("Configure GEOAPIFY_API_KEY no ambiente antes de buscar negócios.")
        wait = self.settings.request_interval - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()
        try:
            response = self.client.get(
                "https://api.geoapify.com/" + endpoint,
                params={**params, "apiKey": key.get_secret_value()},
                timeout=self.settings.request_timeout,
            )
            if response.status_code == 429:
                raise DiscoveryError("Limite da Geoapify atingido (HTTP 429); busca interrompida, sem retries.")
            if response.status_code in {401, 403}:
                raise DiscoveryError("Geoapify recusou a chave ou a autorização (HTTP 401/403).")
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise DiscoveryError("Resposta inválida da Geoapify.")
            return payload
        except httpx.HTTPStatusError as exc:
            raise DiscoveryError(f"Geoapify retornou HTTP {exc.response.status_code}.") from None
        except (httpx.RequestError, ValueError):
            raise DiscoveryError("Falha de conexão ou resposta inválida da Geoapify.") from None

    def search(self, query: str, location: str, limit: int) -> list[Business]:
        if not query.strip() or not location.strip() or not 1 <= limit <= 50:
            raise DiscoveryError("Informe nicho, localização e um limite entre 1 e 50.")
        category = category_for(query)
        geocoding = self._get("v1/geocode/search", text=location, type="locality", limit=1, lang="pt")
        features = geocoding.get("features", [])
        place_id = features[0].get("properties", {}).get("place_id") if features else None
        if not place_id:
            raise DiscoveryError("Localização não encontrada. Informe cidade e estado ou região mais precisa.")
        places = self._get("v2/places", categories=category, filter=f"place:{place_id}", limit=limit, lang="pt")
        businesses = []
        seen = set()
        for feature in places.get("features", [])[:limit]:
            properties = feature.get("properties", {})
            identifier = properties.get("place_id")
            if identifier and identifier in seen:
                continue
            if identifier:
                seen.add(identifier)
                details = self._get("v2/place-details", id=identifier, features="details", lang="pt")
                detail_properties = next((item.get("properties", {}) for item in details.get("features", [])
                                          if item.get("properties", {}).get("feature_type") == "details"), {})
                properties = {**properties, **detail_properties}
            business = self._business(properties, category)
            if business is not None:
                businesses.append(business)
        return businesses

    @staticmethod
    def _business(properties: dict, category: str) -> Business | None:
        name = properties.get("name")
        if not isinstance(name, str) or not name.strip():
            return None  # unnamed POIs are not invented businesses
        url = normalize_website(properties.get("website"))
        evidence = []
        if url and host_matches(url.host, SOCIAL_HOSTS | WHATSAPP_HOSTS):
            kind = "whatsapp_present" if host_matches(url.host, WHATSAPP_HOSTS) else "social_present"
            evidence.append(Evidence(code=kind, description="Canal comercial informado como website pela fonte.",
                                     source="geoapify", source_url=url))
            url = None
        if url:
            evidence.append(Evidence(code="website_found", description="Website oficial informado pela API; validar vínculo manualmente.",
                                     source="geoapify", source_url=url))
        else:
            evidence.append(Evidence(code="website_not_found", description="Website oficial não informado pela fonte; não comprova ausência.",
                                     source="geoapify"))
        contact = properties.get("contact") or {}
        identifier = properties.get("place_id")
        return Business(
            name=normalize_text(name), category=category, address=properties.get("formatted") or None,
            website=url, website_status="found" if url else WebsiteDiscoveryStatus.NOT_FOUND,
            phone=normalize_phone(contact.get("phone")), source="geoapify",
            source_id=str(identifier) if identifier else None, evidence=evidence,
        )
