from uuid import uuid4

import httpx
import pytest

from prospector.analyzers.fetcher import FetchError, PublicFetcher, validate_public_url
from prospector.analyzers.website import HtmlWebsiteAnalyzer
from prospector.config import Settings
from prospector.models import Business


FULL_HTML = """<html><head><title>Alpha</title>
<meta name='description' content='Serviços de barbearia'>
<meta name='viewport' content='width=device-width,initial-scale=1'></head><body>
<h1>Barbearia Alpha</h1><h2>Serviços</h2><p>Cortes de cabelo, barba e serviços de cuidados pessoais para todos os clientes da região.</p>
<a href='tel:+5519999991234'>Telefone</a><a href='https://wa.me/5519999991234'>Fale conosco</a>
<a href='https://www.instagram.com/example'>Instagram</a><a href='https://calendly.com/example'>Agendar horário</a>
<form action='/contact' method='post'><input type='email'><textarea></textarea><button>Solicite orçamento</button></form>
<a href='/broken'>Serviços antigos</a><a href='/ok'>Sobre nós</a></body></html>"""


def analyzer_for(handler, monkeypatch, max_links=5):
    monkeypatch.setattr("prospector.analyzers.fetcher.time.sleep", lambda _: None)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    fetcher = PublicFetcher(client, Settings(), validator=lambda _: None)
    return HtmlWebsiteAnalyzer(fetcher, max_links), client


def business(url="https://example.com"):
    return Business(name="Alpha", source="test", website=url)


def test_full_html_redirects_links_and_contact_signals(monkeypatch):
    requested = []
    def handler(request):
        requested.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /", headers={"content-type": "text/plain"})
        if request.url.path == "/start":
            return httpx.Response(301, headers={"location": "/"})
        if request.url.path == "/broken":
            return httpx.Response(404)
        return httpx.Response(200, text=FULL_HTML, headers={"content-type": "text/html"})
    analyzer, client = analyzer_for(handler, monkeypatch)
    with client:
        result = analyzer.analyze(business("https://example.com/start"), uuid4())
    assert result.status == "completed"
    assert [str(url) for url in result.redirect_chain] == ["https://example.com/start"]
    assert str(result.final_url) == "https://example.com/"
    assert result.title == "Alpha"
    assert result.meta_description == "Serviços de barbearia"
    assert result.headings == ["Barbearia Alpha", "Serviços"]
    for field in ["https", "mobile_viewport", "phone", "whatsapp", "cta", "contact_form", "booking", "social_presence"]:
        assert getattr(result, field) == "present"
    assert [link.status_code for link in result.link_checks] == [404, 200]
    assert all("example.com" == httpx.URL(url).host for url in requested)
    assert result.mobile_performance_score is None


@pytest.mark.parametrize("status, html, content_type", [
    (403, "", "text/html"), (429, "", "text/html"), (500, "", "text/html"),
    (200, "<html><body><div id='app'></div></body></html>", "text/html"),
    (200, "<html>CAPTCHA verify you are human</html>", "text/html"),
    (200, "not HTML", "application/json"),
])
def test_inconclusive_pages_do_not_create_negative_signals(monkeypatch, status, html, content_type):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(status, text=html, headers={"content-type": content_type})
    analyzer, client = analyzer_for(handler, monkeypatch)
    with client:
        result = analyzer.analyze(business(), uuid4())
    assert result.status != "completed"
    for field in ["mobile_viewport", "cta", "booking", "contact_form"]:
        assert getattr(result, field) == "unknown"


def test_robots_disallow_prevents_page_fetch(monkeypatch):
    paths = []
    def handler(request):
        paths.append(request.url.path)
        return httpx.Response(200, text="User-agent: *\nDisallow: /", headers={"content-type": "text/plain"})
    analyzer, client = analyzer_for(handler, monkeypatch)
    with client:
        result = analyzer.analyze(business(), uuid4())
    assert result.status == "failed"
    assert paths == ["/robots.txt"]


def test_private_redirect_is_rejected_before_request(monkeypatch):
    paths = []
    def validator(url):
        if "127.0.0.1" in url:
            raise FetchError("Private address")
    def handler(request):
        paths.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(302, headers={"location": "http://127.0.0.1/"})
    analyzer, client = analyzer_for(handler, monkeypatch)
    analyzer.fetcher.validator = validator
    with client:
        result = analyzer.analyze(business(), uuid4())
    assert result.status == "failed"
    assert all("127.0.0.1" not in path for path in paths)


def test_dns_guard_rejects_private_addresses(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *args: [(2, 1, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(FetchError, match="privados"):
        validate_public_url("https://example.com")


def test_body_size_and_timeout_fail_without_absence(monkeypatch):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text="x" * 2000, headers={"content-type": "text/html"})
    analyzer, client = analyzer_for(handler, monkeypatch)
    analyzer.fetcher.settings.max_body_bytes = 1024
    with client:
        result = analyzer.analyze(business(), uuid4())
    assert result.status == "failed"
    assert result.cta == "unknown"


def test_link_budget_is_enforced(monkeypatch):
    paths = []
    def handler(request):
        paths.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text=FULL_HTML, headers={"content-type": "text/html"})
    analyzer, client = analyzer_for(handler, monkeypatch, max_links=1)
    with client:
        result = analyzer.analyze(business(), uuid4())
    assert len(result.link_checks) == 1
    assert paths == ["/robots.txt", "/", "/broken"]


def test_robots_redirect_is_followed(monkeypatch):
    requested = []
    def handler(request):
        requested.append(str(request.url))
        if request.url.scheme == "http":
            return httpx.Response(301, headers={"location": str(request.url.copy_with(scheme="https"))})
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text=FULL_HTML, headers={"content-type": "text/html"})
    analyzer, client = analyzer_for(handler, monkeypatch, max_links=0)
    with client:
        result = analyzer.analyze(business("http://example.com"), uuid4())
    assert result.status == "completed"
    assert result.https == "present"
    assert requested[:2] == ["http://example.com/robots.txt", "https://example.com/robots.txt"]


def test_robots_redirect_to_private_address_is_rejected(monkeypatch):
    paths = []
    def validator(url):
        if "127.0.0.1" in url:
            raise FetchError("Private address")
    def handler(request):
        paths.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://127.0.0.1/robots.txt"})
    analyzer, client = analyzer_for(handler, monkeypatch)
    analyzer.fetcher.validator = validator
    with client:
        result = analyzer.analyze(business(), uuid4())
    assert result.status == "failed"
    assert paths == ["https://example.com/robots.txt"]


def test_embedded_recaptcha_is_not_a_challenge(monkeypatch):
    html = FULL_HTML.replace("</form>", "<div class='g-recaptcha'></div></form>").replace(
        "</head>", "<script src='https://www.google.com/recaptcha/api.js'></script></head>")
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})
    analyzer, client = analyzer_for(handler, monkeypatch, max_links=0)
    with client:
        result = analyzer.analyze(business(), uuid4())
    assert result.status == "completed"
    assert result.cta == "present"


def test_each_url_is_validated_once(monkeypatch):
    validated = []
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text=FULL_HTML, headers={"content-type": "text/html"})
    analyzer, client = analyzer_for(handler, monkeypatch, max_links=0)
    analyzer.fetcher.validator = validated.append
    with client:
        analyzer.analyze(business(), uuid4())
    assert validated == ["https://example.com/robots.txt", "https://example.com/"]
