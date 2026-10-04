import pytest

from prospector.enrichment.normalization import normalize_phone, normalize_text, normalize_website, host_matches, SOCIAL_HOSTS


@pytest.mark.parametrize("value, expected", [
    (None, None), ("", None), ("javascript:alert(1)", None), ("mailto:a@example.com", None),
    ("ftp://example.com", None), ("https://user:pass@example.com", None),
    ("example.com#section", "https://example.com/"), ("http://example.com", "http://example.com/"),
])
def test_websites(value, expected):
    result = normalize_website(value)
    assert (str(result) if result else None) == expected


@pytest.mark.parametrize("value, expected", [
    (None, None), ("abc", None), ("123", None), ("+55 (19) 99999-1234", "+5519999991234"),
])
def test_phones(value, expected):
    assert normalize_phone(value) == expected


def test_normalization_and_domain_boundaries():
    assert normalize_text("  Barbearia   Alpha\n") == "Barbearia Alpha"
    assert host_matches("www.instagram.com", SOCIAL_HOSTS)
    assert not host_matches("instagram.com.evil.example", SOCIAL_HOSTS)
