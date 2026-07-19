"""Read-side assembly for the Race Intelligence section: recent headlines
(each carrying its own AI relevance blurb) plus the cached AI market
analysis (see app.services.ai_summary / app.services.news)."""

from sqlalchemy.orm import Session

from app.models import Race
from app.services.ai_summary import get_race_intelligence
from app.services.news import get_recent_news


def get_race_intelligence_view(db: Session, race: Race) -> dict:
    intel = get_race_intelligence(db, race.id)

    return {
        "news_articles": get_recent_news(db, race.id),
        "market_analysis": intel.market_analysis if intel is not None else None,
        "market_analysis_generated_at": intel.market_analysis_generated_at if intel is not None else None,
    }
