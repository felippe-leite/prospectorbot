import httpx
import pytest

from prospector.config import Settings
from prospector.discovery.base import DiscoveryError
from prospector.discovery.geoapify import GeoapifyProvider, category_for


def test_geoapify_search_region_details_limit_and_no_invented_fields(monkeypatch):
    monkeypatch.setattr("prospector.discovery.geoapify.time.sleep", lambda _: None)
    requests = []
    def handler(request):
        requests.append(request)
        assert request.url.params["apiKey"] == "test-secret"
        if request.url.path == "/v1/geocode/search":
            return httpx.Response(200, json={"features": [{"properties": {"place_id": "city-id"}}]})
        if request.url.path == "/v2/places":
            assert request.url.params["filter"] == "place:city-id"
            assert request.url.params["limit"] == "2"
            return httpx.Response(200, json={"features": [{"properties": {"name": "Alpha", "place_id": "one"}}, {"properties": {"name": "Beta", "place_id": "two"}}]})
        assert request.url.path == "/v2/place-details"
        identifier = request.url.params["id"]
        return httpx.Response(200, json={"features": [{"properties": {"feature_type": "details", "website": "example.com" if identifier == "one" else None, "contact": {"phone": "+55 (19) 99999-1234"}}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        results = GeoapifyProvider(Settings(geoapify_api_key="test-secret"), client).search("barbearias", "Campinas, SP", 2)
    assert len(requests) == 4
    assert len(results) == 2
    assert str(results[0].website) == "https://example.com/"
    assert results[1].website_status == "not_found"
    assert all(item.review_count is None and item.rating is None for item in results)


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_api_failures_do_not_retry_or_leak_key(status):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(status)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(DiscoveryError) as error:
            GeoapifyProvider(Settings(geoapify_api_key="test-secret"), client).search("barbearias", "Campinas", 30)
    assert len(requests) == 1
    assert "test-secret" not in str(error.value)


def test_social_page_is_not_official_website():
    business = GeoapifyProvider._business({"name": "Alpha", "website": "https://instagram.com/example"}, "service.beauty.hairdresser")
    assert business.website is None
    assert business.evidence[0].code == "social_present"


def test_category_aliases_and_unknown_queries():
    assert category_for("  SALÃO DE BELEZA  ") == "service.beauty.hairdresser"
    with pytest.raises(DiscoveryError):
        category_for("unknown niche")
