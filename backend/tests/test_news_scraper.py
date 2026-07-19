from datetime import datetime, timezone
from unittest.mock import patch

import httpx

from app.ingestion.news_scraper import (
    ScrapedNewsArticle,
    build_news_query,
    fetch_race_news,
    filter_relevant_articles,
)

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Test Race News</title>
<item>
<title>Candidate A holds lead in new poll</title>
<link>https://example.com/article-a</link>
<pubDate>Wed, 15 Jul 2026 12:00:00 GMT</pubDate>
<source url="https://example.com">Example News</source>
</item>
<item>
<title>Fundraising totals released ahead of debate</title>
<link>https://example.com/article-b</link>
<pubDate>Tue, 14 Jul 2026 08:30:00 GMT</pubDate>
<source url="https://otherexample.com">Other Example</source>
</item>
</channel>
</rss>
"""


TEST_REQUEST = httpx.Request("GET", "https://news.google.com/rss/search")


def test_fetch_race_news_parses_items_newest_first():
    response = httpx.Response(200, content=SAMPLE_RSS.encode(), request=TEST_REQUEST)
    with patch("app.ingestion.news_scraper.httpx.get", return_value=response):
        articles = fetch_race_news("California Governor election")

    assert len(articles) == 2
    assert articles[0].headline == "Candidate A holds lead in new poll"
    assert articles[0].source == "Example News"
    assert articles[0].url == "https://example.com/article-a"
    # newest (Jul 15) sorts before older (Jul 14)
    assert articles[0].published_at > articles[1].published_at


def test_fetch_race_news_returns_empty_list_on_http_error():
    with patch("app.ingestion.news_scraper.httpx.get", side_effect=httpx.ConnectError("boom")):
        assert fetch_race_news("anything") == []


def test_fetch_race_news_returns_empty_list_on_http_status_error():
    response = httpx.Response(503, content=b"unavailable", request=httpx.Request("GET", "https://news.google.com"))
    with patch("app.ingestion.news_scraper.httpx.get", return_value=response):
        assert fetch_race_news("anything") == []


def test_fetch_race_news_returns_empty_list_on_malformed_xml():
    response = httpx.Response(200, content=b"not xml at all <<<", request=TEST_REQUEST)
    with patch("app.ingestion.news_scraper.httpx.get", return_value=response):
        assert fetch_race_news("anything") == []


def test_fetch_race_news_skips_items_missing_required_fields():
    rss = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><title>No link here</title><pubDate>Wed, 15 Jul 2026 12:00:00 GMT</pubDate></item>
<item><title>Complete item</title><link>https://example.com/ok</link>
<pubDate>Wed, 15 Jul 2026 12:00:00 GMT</pubDate></item>
</channel></rss>
"""
    response = httpx.Response(200, content=rss.encode(), request=TEST_REQUEST)
    with patch("app.ingestion.news_scraper.httpx.get", return_value=response):
        articles = fetch_race_news("anything")

    assert len(articles) == 1
    assert articles[0].headline == "Complete item"
    # no <source> element -- falls back gracefully instead of crashing
    assert articles[0].source == "Unknown source"


def test_build_news_query_includes_state_and_office():
    query = build_news_query("California", "Governor")
    assert "California" in query
    assert "Governor" in query


def test_build_news_query_quotes_the_state_and_office_phrase():
    # Regression guard: an unquoted query let Google News' loose matching
    # pull in unrelated same-topic roundups about *other* states (see
    # filter_relevant_articles below for the second line of defense).
    query = build_news_query("Texas", "Governor")
    assert '"Texas Governor"' in query


def _article(headline: str) -> ScrapedNewsArticle:
    return ScrapedNewsArticle(
        headline=headline,
        source="Example",
        url=f"https://example.com/{hash(headline)}",
        published_at=datetime.now(timezone.utc),
    )


def test_filter_relevant_articles_drops_headlines_naming_a_different_state():
    # Regression test for a real observed failure: Texas's feed pulled in
    # NYT's templated "<State> Governor Election 2026: Latest Polls" for
    # Nebraska, and a Minnesota-focused Mike Lindell story -- neither
    # mentions Texas at all.
    articles = [
        _article("Nebraska Governor Election 2026: Latest Polls"),
        _article("Mike Lindell Not Registered to Vote in Minnesota, Where He is Running for Governor"),
        _article("Texas Governor Election 2026: Latest Polls"),
        _article("Becerra leads in new statewide poll ahead of debate"),  # no state name at all
    ]

    kept = filter_relevant_articles(articles, "Texas", ["Nebraska", "Minnesota", "California"])

    headlines = {a.headline for a in kept}
    assert headlines == {
        "Texas Governor Election 2026: Latest Polls",
        "Becerra leads in new statewide poll ahead of debate",
    }


def test_filter_relevant_articles_keeps_headline_mentioning_both_states():
    articles = [_article("Texas and Nebraska governor races both tighten in new polling")]
    kept = filter_relevant_articles(articles, "Texas", ["Nebraska"])
    assert len(kept) == 1
