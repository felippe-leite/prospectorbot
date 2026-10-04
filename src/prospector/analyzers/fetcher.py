"""Bounded, identified, public-web GET requests with robots.txt enforcement."""

from dataclasses import dataclass
import ipaddress
import socket
import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from collections.abc import Callable

import httpx

from prospector.config import Settings
from prospector.enrichment.normalization import normalize_website


USER_AGENT = "ProspectorBot/0.1"
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
MAX_REDIRECTS = 5


class FetchError(RuntimeError):
    pass


def validate_public_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise FetchError("URL pública HTTP/HTTPS inválida.")
    if parsed.port not in {None, 80, 443}:
        raise FetchError("Somente portas HTTP/HTTPS padrão são permitidas.")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except OSError:
        raise FetchError("Não foi possível resolver o domínio.") from None
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise FetchError("Endereços locais, privados ou reservados não são analisados.")


def redirect_target(current: str, location: str | None) -> str:
    if not location:
        raise FetchError("Redirect sem destino.")
    destination = normalize_website(str(httpx.URL(current).join(location)))
    if destination is None:
        raise FetchError("Destino de redirect inválido.")
    return str(destination)


@dataclass
class Page:
    url: str
    status_code: int
    text: str
    content_type: str
    elapsed_ms: float
    redirects: list[str]
    location: str | None = None


class PublicFetcher:
    def __init__(self, client: httpx.Client, settings: Settings,
                 validator: Callable[[str], None] = validate_public_url):
        self.client = client
        self.settings = settings
        self.validator = validator
        self._last: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | None] = {}
        self._delays: dict[str, float] = {}
        self._blocked: set[str] = set()

    @staticmethod
    def _origin(url: str) -> str:
        parts = urlsplit(url)
        return f"{parts.scheme}://{parts.netloc}"

    def _request(self, url: str) -> Page:
        self.validator(url)
        origin = self._origin(url)
        if origin in self._blocked:
            raise FetchError("Origem recusou acesso ou atingiu rate limit; sem novas tentativas neste scan.")
        delay = max(self.settings.request_interval, self._delays.get(origin, 0))
        if delay > 60:
            raise FetchError("Crawl-delay excede o orçamento do MVP; análise não realizada.")
        wait = delay - (time.monotonic() - self._last.get(origin, 0))
        if wait > 0:
            time.sleep(wait)
        self._last[origin] = time.monotonic()
        started = time.monotonic()
        try:
            with self.client.stream("GET", url, follow_redirects=False,
                                    timeout=self.settings.request_timeout,
                                    headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.8"}) as response:
                if response.status_code in {401, 403, 429}:
                    self._blocked.add(origin)
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > self.settings.max_body_bytes:
                        raise FetchError("Resposta excede o tamanho máximo permitido.")
                    if time.monotonic() - started > self.settings.request_timeout:
                        raise FetchError("Resposta excede o tempo máximo permitido.")
                text = body.decode(response.encoding or "utf-8", errors="replace")
                return Page(str(response.url), response.status_code, text,
                            response.headers.get("content-type", ""),
                            (time.monotonic() - started) * 1000, [], response.headers.get("location"))
        except (httpx.RequestError, LookupError):
            raise FetchError("Falha de conexão, timeout ou TLS; nenhuma conclusão sobre o HTML.") from None

    def _robots_page(self, origin: str) -> Page:
        # RFC 9309: follow robots.txt redirects (http→https, www); each hop is validated.
        url = origin + "/robots.txt"
        for _ in range(MAX_REDIRECTS + 1):
            page = self._request(url)
            if page.status_code not in REDIRECT_STATUSES:
                return page
            url = redirect_target(url, page.location)
        raise FetchError("robots.txt excede o limite de redirects; análise não realizada.")

    def _allowed(self, url: str) -> None:
        origin = self._origin(url)
        if origin not in self._robots:
            # Fail closed on access restrictions or temporary errors.
            self._robots[origin] = None
            page = self._robots_page(origin)
            if page.status_code == 404:
                parser = RobotFileParser()
                parser.parse([])
            elif page.status_code == 200 and "text/html" not in page.content_type:
                parser = RobotFileParser()
                parser.parse(page.text.splitlines())
            else:
                raise FetchError("robots.txt indisponível ou restrito; análise não realizada.")
            self._robots[origin] = parser
            self._delays[origin] = parser.crawl_delay(USER_AGENT) or parser.crawl_delay("*") or 0
            rate = parser.request_rate(USER_AGENT) or parser.request_rate("*")
            if rate and rate.requests > 0:
                self._delays[origin] = max(self._delays[origin], rate.seconds / rate.requests)
        parser = self._robots[origin]
        if parser is None or not parser.can_fetch(USER_AGENT, url):
            raise FetchError("robots.txt impede ou não permite confirmar o acesso a esta página.")

    def fetch(self, url: str) -> Page:
        current = url
        redirects: list[str] = []
        elapsed = 0.0
        for _ in range(MAX_REDIRECTS + 1):
            # _request validates every URL, including the robots.txt of the origin.
            self._allowed(current)
            page = self._request(current)
            elapsed += page.elapsed_ms
            if page.status_code in REDIRECT_STATUSES:
                redirects.append(current)
                current = redirect_target(current, page.location)
                continue
            page.redirects = redirects
            page.elapsed_ms = elapsed
            return page
        raise FetchError("Limite de redirects atingido.")
