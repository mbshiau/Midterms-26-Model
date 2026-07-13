from unittest.mock import Mock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.hashes import SHA256

from app.config import settings
from app.ingestion.kalshi_scraper import fetch_market_odds

_TEST_KEY_ID = "test-key-id"
_TEST_TICKER = "KXGOVCA-26-XBEC"

# Real response captured 2026-07-13 from GET /trade-api/v2/markets/KXGOVCA-26-XBEC
# (Xavier Becerra's "will win California's governorship" market) -- confirms
# Kalshi reports prices as dollar-denominated decimal strings, not integer
# cents, on the current (api.elections.kalshi.com) API.
REAL_ACTIVE_MARKET_RESPONSE = {
    "market": {
        "ticker": "KXGOVCA-26-XBEC",
        "title": "Who will win the governorship in California?",
        "status": "active",
        "yes_bid_dollars": "0.9320",
        "yes_ask_dollars": "0.9350",
        "last_price_dollars": "0.9340",
        "no_bid_dollars": "0.0650",
        "no_ask_dollars": "0.0680",
    }
}

# Real response shape for a newly-listed, untraded market (e.g. Alabama's
# governor race this far out) -- every price field is omitted entirely
# rather than sent as null.
REAL_UNTRADED_MARKET_RESPONSE = {"market": {"ticker": "GOVPARTYAL-26-D", "status": "active"}}


def _write_test_private_key(path) -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    path.write_bytes(pem)
    return key


def _configure_credentials(tmp_path, monkeypatch):
    key = _write_test_private_key(tmp_path / "kalshi_private_key.pem")
    monkeypatch.setattr(settings, "kalshi_api_key_id", _TEST_KEY_ID)
    monkeypatch.setattr(settings, "kalshi_private_key_path", str(tmp_path / "kalshi_private_key.pem"))
    return key


def _mock_response(json_body: dict, status_code: int = 200) -> Mock:
    resp = Mock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    resp.raise_for_status = Mock()
    if status_code >= 400:
        import httpx

        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=Mock(), response=resp
        )
    return resp


def test_fetch_market_odds_returns_none_without_credentials(monkeypatch):
    monkeypatch.setattr(settings, "kalshi_api_key_id", "")
    monkeypatch.setattr(settings, "kalshi_private_key_path", "")
    assert fetch_market_odds(_TEST_TICKER) is None


def test_fetch_market_odds_uses_bid_ask_midpoint_on_a_real_active_market(tmp_path, monkeypatch):
    _configure_credentials(tmp_path, monkeypatch)
    response = _mock_response(REAL_ACTIVE_MARKET_RESPONSE)

    with patch("app.ingestion.kalshi_scraper.httpx.get", return_value=response) as mock_get:
        result = fetch_market_odds(_TEST_TICKER)

    assert result is not None
    assert result.ticker == _TEST_TICKER
    # (0.9320 + 0.9350) / 2 * 100 -- the bid/ask midpoint, not last_price_dollars.
    assert result.yes_price_pct == pytest.approx(93.35)
    assert result.source_url == "https://kalshi.com/markets/kxgovca-26-xbec"

    # A real signed request was made with the right headers present.
    _, kwargs = mock_get.call_args
    headers = kwargs["headers"]
    assert headers["KALSHI-ACCESS-KEY"] == _TEST_KEY_ID
    assert "KALSHI-ACCESS-SIGNATURE" in headers
    assert "KALSHI-ACCESS-TIMESTAMP" in headers


def test_fetch_market_odds_falls_back_to_last_price_without_bid_ask(tmp_path, monkeypatch):
    _configure_credentials(tmp_path, monkeypatch)
    response = _mock_response({"market": {"last_price_dollars": "0.5500"}})

    with patch("app.ingestion.kalshi_scraper.httpx.get", return_value=response):
        result = fetch_market_odds(_TEST_TICKER)

    assert result is not None
    assert result.yes_price_pct == pytest.approx(55.0)


def test_fetch_market_odds_signature_verifies_against_the_public_key(tmp_path, monkeypatch):
    key = _configure_credentials(tmp_path, monkeypatch)
    response = _mock_response(REAL_ACTIVE_MARKET_RESPONSE)

    with patch("app.ingestion.kalshi_scraper.httpx.get", return_value=response) as mock_get:
        fetch_market_odds(_TEST_TICKER)

    _, kwargs = mock_get.call_args
    headers = kwargs["headers"]
    timestamp = headers["KALSHI-ACCESS-TIMESTAMP"]
    import base64

    signature = base64.b64decode(headers["KALSHI-ACCESS-SIGNATURE"])
    message = (timestamp + "GET" + f"/trade-api/v2/markets/{_TEST_TICKER}").encode("utf-8")

    # Raises if the signature doesn't verify against the message -- proves
    # the signed string matches Kalshi's documented `timestamp + method +
    # path` scheme, not just that *some* signature was sent.
    key.public_key().verify(
        signature,
        message,
        padding.PSS(mgf=padding.MGF1(SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
        SHA256(),
    )


def test_fetch_market_odds_returns_none_on_http_error(tmp_path, monkeypatch):
    _configure_credentials(tmp_path, monkeypatch)
    response = _mock_response({}, status_code=404)

    with patch("app.ingestion.kalshi_scraper.httpx.get", return_value=response):
        assert fetch_market_odds("KXGOVXX-26-NOTLISTED") is None


def test_fetch_market_odds_returns_none_on_missing_key_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "kalshi_api_key_id", _TEST_KEY_ID)
    monkeypatch.setattr(settings, "kalshi_private_key_path", str(tmp_path / "does_not_exist.pem"))
    assert fetch_market_odds(_TEST_TICKER) is None


def test_fetch_market_odds_returns_none_on_malformed_response(tmp_path, monkeypatch):
    _configure_credentials(tmp_path, monkeypatch)
    response = _mock_response({"market": {}})

    with patch("app.ingestion.kalshi_scraper.httpx.get", return_value=response):
        assert fetch_market_odds(_TEST_TICKER) is None


def test_fetch_market_odds_returns_none_for_a_real_untraded_market(tmp_path, monkeypatch):
    # A market that's listed but has had zero trades yet (this far from the
    # 2026 election) omits every price field entirely rather than sending
    # it as null.
    _configure_credentials(tmp_path, monkeypatch)
    response = _mock_response(REAL_UNTRADED_MARKET_RESPONSE)

    with patch("app.ingestion.kalshi_scraper.httpx.get", return_value=response):
        assert fetch_market_odds("GOVPARTYAL-26-D") is None
