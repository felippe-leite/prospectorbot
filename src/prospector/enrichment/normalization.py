"""Minimal normalization: never infer missing commercial information."""

import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit

from pydantic import HttpUrl, TypeAdapter, ValidationError


SOCIAL_HOSTS = {"instagram.com", "facebook.com", "fb.com", "tiktok.com", "linkedin.com", "youtube.com", "x.com", "twitter.com"}
WHATSAPP_HOSTS = {"wa.me", "api.whatsapp.com", "web.whatsapp.com", "whatsapp.com"}


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def search_key(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKD", normalize_text(value).casefold())
                   if not unicodedata.combining(char))


def host_matches(host: str, domains: set[str]) -> bool:
    host = host.lower().rstrip(".")
    return any(host == domain or host.endswith("." + domain) for domain in domains)


def normalize_website(value: object) -> HttpUrl | None:
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    if "://" not in value:
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", value) and not re.search(r":\d+(?:/|$)", value):
            return None
        value = "https://" + value
    try:
        url = TypeAdapter(HttpUrl).validate_python(value)
    except ValidationError:
        return None
    if url.username or url.password or not url.host or "." not in url.host:
        return None
    parts = urlsplit(str(url))
    return TypeAdapter(HttpUrl).validate_python(urlunsplit(parts._replace(fragment="")))


def normalize_phone(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    digits = re.sub(r"\D", "", value)
    if not 7 <= len(digits) <= 15:
        return None
    return ("+" if value.strip().startswith("+") else "") + digits
