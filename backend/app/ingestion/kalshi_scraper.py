"""Live Kalshi market-price fetcher: pulls a candidate's "will win" YES
contract price from Kalshi's REST API.

Unlike Wikipedia (see wikipedia_scraper.py), Kalshi requires an RSA-signed
request for *every* endpoint, including read-only market data -- there is no
anonymous scrape path. Auth is per Kalshi's documented scheme: sign
`timestamp_ms + method + path` with the account's RSA private key
(PSS padding, SHA-256), and send the key id, signature, and timestamp as
headers. The key pair comes from the user's own Kalshi account (Account
Settings -> API Keys), configured via settings.kalshi_api_key_id /
settings.kalshi_private_key_path -- never hardcoded or committed.

Returns None on any failure (missing credentials, network error, unlisted
ticker, unexpected response shape) -- exactly like wikipedia_scraper and
approval_scraper, so a Kalshi outage or a not-yet-listed market never blocks
the scheduled refresh job, just leaves that candidate's market odds
unchanged until the next run.
"""

import base64
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.config import settings

logger = logging.getLogger(__name__)

API_PATH_PREFIX = "/trade-api/v2"
REQUEST_TIMEOUT_SECONDS = 15


@dataclass
class ScrapedMarketOdds:
    ticker: str
    yes_price_pct: float
    as_of: datetime
    source_url: str


@dataclass
class ScrapedHouseMarket:
    ticker: str
    # "Republican party"/"Democratic party" for a standard 2-candidate race's
    # party-outcome market, or a candidate's own name for a market keyed to
    # a specific candidate (e.g. a real independent/third-party contender) --
    # whichever Kalshi's own yes_sub_title says this market resolves on.
    # scripts/backfill_kalshi_tickers.py matches this back to a HOUSE_RACES
    # candidate by party or by name; never guessed from the ticker string.
    yes_sub_title: str | None


def fetch_house_race_markets(state_code: str, district: int) -> list[ScrapedHouseMarket] | None:
    """Real market list for one House district's race, via Kalshi's own
    `event_ticker=KXHOUSERACE-{STATE}{DD}-26` filter -- confirmed against
    Kalshi's actual listings (see conversation) rather than guessed from a
    naming pattern, since some districts (e.g. a race with a real
    independent candidate) get a market per named candidate instead of one
    per party. Returns None on missing credentials/network failure (same
    fail-soft convention as fetch_market_odds); [] if Kalshi simply hasn't
    listed this district yet."""
    if not settings.kalshi_api_key_id or not settings.kalshi_private_key_path:
        return None

    event_ticker = f"KXHOUSERACE-{state_code.upper()}{district:02d}-26"
    path = "/trade-api/v2/markets"
    try:
        headers = _auth_headers("GET", path)
        resp = httpx.get(
            f"{settings.kalshi_base_url}/markets",
            headers=headers,
            params={"event_ticker": event_ticker},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        markets = resp.json().get("markets", [])
        return [
            ScrapedHouseMarket(ticker=m["ticker"], yes_sub_title=m.get("yes_sub_title"))
            for m in markets
        ]
    except (httpx.HTTPError, KeyError, ValueError, OSError) as e:
        logger.warning("Kalshi market list fetch failed for %r: %s", event_ticker, e)
        return None


def _load_private_key():
    with open(settings.kalshi_private_key_path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def _sign(private_key, message: str) -> str:
    signature = private_key.sign(
        message.encode("utf-8"),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")


def _auth_headers(method: str, path: str) -> dict[str, str]:
    private_key = _load_private_key()
    timestamp_ms = str(int(time.time() * 1000))
    signature = _sign(private_key, timestamp_ms + method + path)
    return {
        "KALSHI-ACCESS-KEY": settings.kalshi_api_key_id,
        "KALSHI-ACCESS-SIGNATURE": signature,
        "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
    }


def fetch_market_odds(ticker: str) -> ScrapedMarketOdds | None:
    """Fetches one market's current YES price (0-100, the market-implied
    probability the ticker's outcome happens -- e.g. that candidate wins)."""
    if not settings.kalshi_api_key_id or not settings.kalshi_private_key_path:
        return None

    path = f"{API_PATH_PREFIX}/markets/{ticker}"
    try:
        headers = _auth_headers("GET", path)
        resp = httpx.get(
            f"{settings.kalshi_base_url}/markets/{ticker}",
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        market = resp.json()["market"]

        # Kalshi's current API reports prices as dollar-denominated decimal
        # strings (e.g. "0.9340" = 93.40 cents = a 93.4% implied
        # probability), not integer cents -- *_dollars is the live field
        # name, the plain yes_bid/yes_ask/last_price fields from Kalshi's
        # older docs no longer exist on this response.
        yes_bid_dollars = market.get("yes_bid_dollars")
        yes_ask_dollars = market.get("yes_ask_dollars")
        if yes_bid_dollars is not None and yes_ask_dollars is not None:
            # Bid/ask midpoint is a steadier probability estimate than the
            # last trade, which can be stale on a thinly-traded market.
            yes_price_pct = (float(yes_bid_dollars) + float(yes_ask_dollars)) / 2 * 100
        else:
            last_price_dollars = market.get("last_price_dollars")
            if last_price_dollars is None:
                # A market with zero trades yet (this far from the
                # election) omits every price field entirely rather than
                # sending it as null. That's "no data available", not an
                # error worth logging every scheduled run, so it's quiet
                # here (unlike the warning below for genuine failures).
                return None
            yes_price_pct = float(last_price_dollars) * 100

        return ScrapedMarketOdds(
            ticker=ticker,
            yes_price_pct=yes_price_pct,
            as_of=datetime.now(timezone.utc),
            source_url=f"https://kalshi.com/markets/{ticker.lower()}",
        )
    except (httpx.HTTPError, KeyError, ValueError, OSError) as e:
        logger.warning("Kalshi fetch failed for %r: %s", ticker, e)
        return None
