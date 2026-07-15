"""Reads/writes the single current GenericBallot row that feeds the
fundamentals model's national-environment adjustment alongside presidential
approval."""

from datetime import date

from sqlalchemy.orm import Session

from app.data.fundamentals_data import GENERIC_BALLOT
from app.ingestion.generic_ballot_scraper import ScrapedGenericBallot
from app.models import GenericBallot


def seed_default_generic_ballot(db: Session) -> GenericBallot:
    """Ensures a row exists, using the static researched default if empty."""
    existing = db.query(GenericBallot).first()
    if existing is not None:
        return existing

    row = GenericBallot(
        dem_pct=GENERIC_BALLOT["dem_pct"],
        rep_pct=GENERIC_BALLOT["rep_pct"],
        as_of=date.fromisoformat(GENERIC_BALLOT["as_of"]),
        source_url=GENERIC_BALLOT["source_url"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_current_generic_ballot(db: Session) -> GenericBallot:
    existing = db.query(GenericBallot).order_by(GenericBallot.updated_at.desc()).first()
    return existing if existing is not None else seed_default_generic_ballot(db)


def update_generic_ballot(db: Session, scraped: ScrapedGenericBallot) -> GenericBallot:
    """Upserts the single current-generic-ballot row in place (no history kept)."""
    row = db.query(GenericBallot).order_by(GenericBallot.updated_at.desc()).first()
    if row is None:
        row = GenericBallot(dem_pct=0, rep_pct=0, as_of=scraped.as_of, source_url="")
        db.add(row)

    row.dem_pct = scraped.dem_pct
    row.rep_pct = scraped.rep_pct
    row.as_of = scraped.as_of
    row.source_url = scraped.source_url
    db.commit()
    db.refresh(row)
    return row
