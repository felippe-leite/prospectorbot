from contextlib import contextmanager
import threading
import time

from fastapi.testclient import TestClient
import pytest

from prospector.api.app import create_app
from prospector.config import Settings
from prospector.models import Business, CheckStatus, Evidence, WebsiteAnalysis


class Provider:
    def search(self, query, location, limit):
        return [
            Business(name="Barbearia Alpha", source="test", source_id="1", category="service.beauty.hairdresser",
                     website_status="not_found",
                     review_count=80, evidence=[Evidence(code="whatsapp_present", description="WhatsApp",
                                                         source="test", source_url="https://wa.me/5519999999999")]),
            Business(name="Beta Cortes", source="test", source_id="2", category="service.beauty.hairdresser",
                     website="https://beta.example.com"),
        ][:limit]


class Analyzer:
    def analyze(self, business, scan_id):
        return WebsiteAnalysis(business_id=business.id, scan_id=scan_id, requested_url=business.website,
                               final_url=business.website, status="completed", status_code=200,
                               response_time_ms=4200, https=CheckStatus.PRESENT,
                               mobile_viewport=CheckStatus.ABSENT, cta=CheckStatus.ABSENT,
                               booking=CheckStatus.ABSENT, title_status=CheckStatus.PRESENT,
                               meta_description_status=CheckStatus.ABSENT)


@contextmanager
def fake_pipeline(settings):
    yield Provider(), Analyzer()


@pytest.fixture
def client(tmp_path):
    settings = Settings(database_path=tmp_path / "api.db", geoapify_api_key="test-key")
    with TestClient(create_app(settings, fake_pipeline)) as test_client:
        yield test_client


def wait_for(client, scan_id):
    for _ in range(200):
        body = client.get(f"/api/scans/{scan_id}").json()
        if body["scan"]["status"] in {"completed", "failed"}:
            return body
        time.sleep(0.02)
    raise AssertionError("scan did not finish")


def test_scan_flow_leads_detail_and_tracking(client):
    health = client.get("/api/health").json()
    assert health["discovery_configured"] is True and health["performance_configured"] is False
    response = client.post("/api/scans", json={"query": "Barbershops", "location": "Campinas, SP", "limit": 30})
    assert response.status_code == 202
    scan = wait_for(client, response.json()["scan"]["id"])
    assert scan["scan"]["status"] == "completed"
    assert scan["analyzed"] == 2 and scan["progress"] is None

    leads = client.get("/api/leads").json()
    assert [lead["name"] for lead in leads] == ["Beta Cortes", "Barbearia Alpha"]
    assert leads[0]["score"] == 45 and leads[0]["classification"] == "Moderate"
    assert set(leads[0]["tags"]) == {"website_redesign", "performance", "booking", "seo"}
    assert leads[1]["tags"] == ["landing_page"] and leads[1]["status"] == "new"
    assert client.get("/api/leads", params={"tag": "landing_page"}).json()[0]["name"] == "Barbearia Alpha"

    assert [lead["name"] for lead in client.get("/api/leads", params={"website": "none"}).json()] == ["Barbearia Alpha"]
    assert client.get("/api/leads", params={"q": "beta", "tag": "seo", "min_score": 40}).json()[0]["name"] == "Beta Cortes"
    assert client.get("/api/leads", params={"classification": "Gold Nugget"}).json() == []

    beta = leads[0]["business_id"]
    detail = client.get(f"/api/leads/{beta}").json()
    assert detail["analysis"]["status_code"] == 200
    assert [item["rule_code"] for item in detail["contributions"]][0] == "no_booking"
    assert {item["rule_code"]: item["points"] for item in detail["opportunities"]}["missing_description"] == 0
    assert len(detail["appearances"]) == 1

    tracking = client.patch(f"/api/leads/{beta}", json={"status": "interesting", "notes": "Ver Instagram."}).json()
    assert tracking["status"] == "interesting" and tracking["updated_at"]
    client.patch(f"/api/leads/{beta}", json={"notes": "Atualizado"})
    saved = client.get(f"/api/leads/{beta}").json()["tracking"]
    assert (saved["status"], saved["notes"]) == ("interesting", "Atualizado")
    assert client.get("/api/leads", params={"status": "interesting"}).json()[0]["business_id"] == beta

    stats = client.get("/api/stats").json()
    assert stats == {"businesses": 2, "opportunities": 6, "gold_nuggets": 0, "average_score": 30.0, "scans": 1}


def test_repeated_scans_keep_latest_snapshot_per_business(client):
    for _ in range(2):
        wait_for(client, client.post("/api/scans", json={"query": "barbearias", "location": "Campinas"}).json()["scan"]["id"])
    assert len(client.get("/api/scans").json()) == 2
    leads = client.get("/api/leads").json()
    assert len(leads) == 2
    assert len(client.get(f"/api/leads/{leads[0]['business_id']}").json()["appearances"]) == 2


def test_scan_validation_errors(client, tmp_path):
    names = client.get("/api/categories").json()
    assert "oficina mecanica" in names and "barbershops" in names
    assert "astronauts" in client.post("/api/scans", json={"query": "astronauts", "location": "Campinas"}).json()["detail"]
    assert client.post("/api/scans", json={"query": "astronauts", "location": "Campinas"}).status_code == 422
    assert client.post("/api/scans", json={"query": "barbearias", "location": "Campinas", "limit": 51}).status_code == 422
    assert client.get("/api/scans/00000000-0000-0000-0000-000000000000").status_code == 404
    assert client.patch("/api/leads/00000000-0000-0000-0000-000000000000", json={"status": "won"}).status_code == 404
    with TestClient(create_app(Settings(database_path=tmp_path / "nokey.db"), fake_pipeline)) as no_key:
        assert no_key.post("/api/scans", json={"query": "barbearias", "location": "Campinas"}).status_code == 503


def test_only_one_scan_runs_at_a_time_and_progress_is_live(tmp_path):
    release = threading.Event()

    class SlowAnalyzer(Analyzer):
        def analyze(self, business, scan_id):
            release.wait(5)
            return super().analyze(business, scan_id)

    @contextmanager
    def slow_pipeline(settings):
        yield Provider(), SlowAnalyzer()

    settings = Settings(database_path=tmp_path / "slow.db", geoapify_api_key="test-key")
    with TestClient(create_app(settings, slow_pipeline)) as client:
        scan_id = client.post("/api/scans", json={"query": "barbearias", "location": "Campinas"}).json()["scan"]["id"]
        for _ in range(200):
            progress = client.get(f"/api/scans/{scan_id}").json()["progress"]
            if progress and progress["stage"] == "website_analysis":
                break
            time.sleep(0.01)
        assert progress == {"stage": "website_analysis", "analyzed": 1, "total": 2,
                            "current_business": "Beta Cortes", "has_website": True}
        assert client.post("/api/scans", json={"query": "barbearias", "location": "Campinas"}).status_code == 409
        assert client.delete("/api/data").status_code == 409
        release.set()
        assert wait_for(client, scan_id)["scan"]["status"] == "completed"


def test_manual_enrichment_rescores_and_survives_new_scans(client):
    wait_for(client, client.post("/api/scans", json={"query": "barbearias", "location": "Campinas"}).json()["scan"]["id"])
    alpha = next(lead for lead in client.get("/api/leads").json() if lead["name"] == "Barbearia Alpha")
    assert alpha["score"] == 15

    bad = client.patch(f"/api/leads/{alpha['business_id']}", json={"website": "instagram.com/alpha"})
    assert bad.status_code == 422
    saved = client.patch(f"/api/leads/{alpha['business_id']}",
                         json={"no_website": True, "instagram": "@barbearia.alpha", "phone": "(19) 99999-0000"}).json()
    assert saved["instagram"] == "https://www.instagram.com/barbearia.alpha/" and saved["no_website"] is True

    rescore = client.post(f"/api/leads/{alpha['business_id']}/rescore")
    assert rescore.status_code == 202 and rescore.json()["scan"]["kind"] == "manual"
    wait_for(client, rescore.json()["scan"]["id"])
    detail = client.get(f"/api/leads/{alpha['business_id']}").json()
    assert detail["score"] == 45 and detail["scan"]["kind"] == "manual"
    assert detail["tracking"]["phone"] == "+5519999990000" and detail["business"]["phone"] is None
    assert {item["rule_code"] for item in detail["contributions"]} >= {"no_website", "social_present"}
    assert client.get("/api/stats").json()["scans"] == 1

    # A later discovery scan re-applies the verified data instead of dropping the score.
    wait_for(client, client.post("/api/scans", json={"query": "barbearias", "location": "Campinas"}).json()["scan"]["id"])
    assert client.get(f"/api/leads/{alpha['business_id']}").json()["score"] == 45

    # Clearing the confirmation goes back to the unscored state on the next update.
    client.patch(f"/api/leads/{alpha['business_id']}", json={"no_website": False, "instagram": None})
    wait_for(client, client.post(f"/api/leads/{alpha['business_id']}/rescore").json()["scan"]["id"])
    assert client.get(f"/api/leads/{alpha['business_id']}").json()["score"] == 15


def test_location_suggestions_strip_country_and_are_cached(client, monkeypatch):
    import httpx
    from prospector.discovery.geoapify import GeoapifyProvider
    monkeypatch.setattr("prospector.discovery.geoapify.time.sleep", lambda _: None)
    calls = []

    def handler(request):
        calls.append(request)
        assert request.url.params["filter"] == "countrycode:br" and request.url.params["apiKey"] == "test-key"
        return httpx.Response(200, json={"results": [
            {"result_type": "city", "formatted": "Campinas, SP, Brasil", "country": "Brasil"},
            {"result_type": "city", "formatted": "Campina Grande, PB, Brasil", "country": "Brasil"},
            {"result_type": "street", "formatted": "Rua Campinas, Santos, SP, Brasil", "country": "Brasil"},
        ]})

    settings = Settings(database_path="unused.db", geoapify_api_key="test-key")
    client.app.state.locations = GeoapifyProvider(settings, httpx.Client(transport=httpx.MockTransport(handler)))
    assert client.get("/api/locations", params={"q": "Campin"}).json() == ["Campinas, SP", "Campina Grande, PB"]
    client.get("/api/locations", params={"q": "campin"})
    assert len(calls) == 1
    assert client.get("/api/locations", params={"q": "C"}).status_code == 422


def test_clear_data_removes_everything(client):
    wait_for(client, client.post("/api/scans", json={"query": "barbearias", "location": "Campinas"}).json()["scan"]["id"])
    lead = client.get("/api/leads").json()[0]
    client.patch(f"/api/leads/{lead['business_id']}", json={"notes": "x", "no_website": True})
    assert client.delete("/api/data").status_code == 204
    assert client.get("/api/leads").json() == [] and client.get("/api/scans").json() == []
    assert client.get("/api/stats").json()["businesses"] == 0
    # Running a new scan afterwards works on the emptied database.
    assert wait_for(client, client.post("/api/scans", json={"query": "barbearias", "location": "Campinas"}).json()["scan"]["id"])["analyzed"] == 2
