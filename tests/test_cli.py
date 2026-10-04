import json
from uuid import UUID

import httpx
from typer.testing import CliRunner

from prospector.config import Settings
from prospector.database.repository import Repository
from prospector.database.session import create_database_engine, create_session_factory, session_scope
from prospector.main import app


runner = CliRunner()


def test_cli_30_businesses_full_flow_history_and_report(tmp_path, monkeypatch):
    settings = Settings(database_path=tmp_path / "prospector.db", geoapify_api_key="test-key", max_links=0)
    monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls: settings))
    monkeypatch.setattr("time.sleep", lambda _: None)
    monkeypatch.setattr("socket.getaddrinfo", lambda *args: [(2, 1, 6, "", ("93.184.216.34", 443))])
    requests = []
    html = """<html><head><title>Barbearia</title></head><body><h1>Serviços de barbearia</h1>
    <p>Conheça os serviços de corte de cabelo, barba e cuidados pessoais do nosso estabelecimento na região.</p>
    <a href='https://wa.me/5519999991234'>WhatsApp</a></body></html>"""
    def handler(request):
        requests.append(request)
        if request.url.host == "api.geoapify.com":
            if request.url.path == "/v1/geocode/search":
                data = {"features": [{"properties": {"place_id": "city"}}]}
            elif request.url.path == "/v2/places":
                data = {"features": [{"properties": {"name": f"Barbearia {i}", "place_id": str(i)}} for i in range(30)]}
            else:
                identifier = request.url.params["id"]
                data = {"features": [{"properties": {"feature_type": "details", "website": f"https://example.com/business/{identifier}"}}]}
            return httpx.Response(200, json=data)
        assert request.url.host == "example.com"
        assert "apiKey" not in request.url.params
        assert request.method == "GET"
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})
    original_client = httpx.Client
    monkeypatch.setattr("prospector.pipeline.httpx.Client", lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs))
    report = tmp_path / "reports" / "report.json"  # missing folder is created
    result = runner.invoke(app, ["scan", "--query", "barbearias", "--location", "Campinas, SP", "--limit", "30", "--output", str(report)])
    assert result.exit_code == 0, result.output
    assert "30 negócios avaliados" in result.output
    data = json.loads(report.read_text())
    assert len(data["leads"]) == 30
    assert {lead["score"]["value"] for lead in data["leads"]} == {40}
    assert "Geoapify" in data["attribution"]
    scan_id = data["scan"]["id"]
    prior_requests = len(requests)
    result = runner.invoke(app, ["leads"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["show", "1"])
    assert result.exit_code == 0
    assert "Evidence / pontuação" in result.output
    assert "Inferência" in result.output
    assert len(requests) == prior_requests  # stored reports are offline
    second = runner.invoke(app, ["scan", "--query", "barbearias", "--location", "Campinas, SP", "--limit", "30"])
    assert second.exit_code == 0, second.output
    engine = create_database_engine(settings)
    try:
        with session_scope(create_session_factory(engine)) as session:
            repo = Repository(session)
            assert len(repo.list_businesses()) == 30
            assert len(repo.list_scans()) == 2
            assert len(repo.list_scores(UUID(scan_id))) == 30
    finally:
        engine.dispose()
    assert runner.invoke(app, ["leads", "--scan", scan_id]).exit_code == 0
    assert runner.invoke(app, ["show", "31"]).exit_code == 1


def test_cli_missing_key_and_invalid_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls: Settings(database_path=tmp_path / "db.sqlite")))
    assert runner.invoke(app, ["scan", "--query", "barbearias", "--location", "Campinas"]).exit_code == 1
    assert runner.invoke(app, ["scan", "--query", "barbearias", "--location", "Campinas", "--limit", "51"]).exit_code == 2
    assert runner.invoke(app, ["leads"]).exit_code == 1
    assert runner.invoke(app, ["categories"]).exit_code == 0
    assert runner.invoke(app, ["--help"]).exit_code == 0
