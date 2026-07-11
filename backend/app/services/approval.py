"""Reads/writes the single current PresidentApproval row that feeds the
fundamentals model's national-environment adjustment."""

from datetime import date

from sqlalchemy.orm import Session

from app.data.fundamentals_data import PRESIDENT
from app.ingestion.approval_scraper import ScrapedApproval
from app.models import PresidentApproval


def seed_default_approval(db: Session) -> PresidentApproval:
    """Ensures a row exists, using the static researched default if empty."""
    existing = db.query(PresidentApproval).first()
    if existing is not None:
        return existing

    row = PresidentApproval(
        name=PRESIDENT["name"],
        party=PRESIDENT["party"],
        approval_pct=PRESIDENT["approval_pct"],
        as_of=date.fromisoformat(PRESIDENT["as_of"]),
        source_url="https://en.wikipedia.org/wiki/Opinion_polling_on_the_second_Trump_presidency",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_current_approval(db: Session) -> PresidentApproval:
    existing = db.query(PresidentApproval).order_by(PresidentApproval.updated_at.desc()).first()
    return existing if existing is not None else seed_default_approval(db)


def update_approval(db: Session, scraped: ScrapedApproval, party: str, name: str) -> PresidentApproval:
    """Upserts the single current-approval row in place (no history kept)."""
    row = db.query(PresidentApproval).order_by(PresidentApproval.updated_at.desc()).first()
    if row is None:
        row = PresidentApproval(name=name, party=party, approval_pct=0, as_of=scraped.as_of, source_url="")
        db.add(row)

    row.name = name
    row.party = party
    row.approval_pct = scraped.approval_pct
    row.as_of = scraped.as_of
    row.source_url = scraped.source_url
    db.commit()
    db.refresh(row)
    return row
