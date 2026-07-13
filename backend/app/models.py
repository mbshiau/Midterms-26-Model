import enum
from datetime import date, datetime, timezone

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Date, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Population(str, enum.Enum):
    LV = "LV"  # likely voters
    RV = "RV"  # registered voters
    A = "A"  # all adults


class Race(Base):
    """A single state's governor race — the unit everything else is scoped
    to. Adding a new state means adding a Race row plus its seed/fundamentals
    data, not a schema change."""

    __tablename__ = "races"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    state_code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)
    state_name: Mapped[str] = mapped_column(String(100), nullable=False)
    office: Mapped[str] = mapped_column(String(100), default="Governor")
    election_date: Mapped[date] = mapped_column(Date, nullable=False)
    wikipedia_page_title: Mapped[str] = mapped_column(String(200), nullable=False)

    candidates: Mapped[list["Candidate"]] = relationship(back_populates="race")
    polls: Mapped[list["Poll"]] = relationship(back_populates="race")
    forecast_snapshots: Mapped[list["ForecastSnapshot"]] = relationship(back_populates="race")


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    party: Mapped[str] = mapped_column(String(40), nullable=False)
    incumbent: Mapped[bool] = mapped_column(default=False)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    race: Mapped["Race"] = relationship(back_populates="candidates")
    poll_results: Mapped[list["PollResult"]] = relationship(back_populates="candidate")
    forecast_results: Mapped[list["ForecastResult"]] = relationship(back_populates="candidate")


class Poll(Base):
    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), nullable=False)
    pollster: Mapped[str] = mapped_column(String(200), nullable=False)
    sponsor: Mapped[str | None] = mapped_column(String(200), nullable=True)
    field_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    field_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    release_date: Mapped[date] = mapped_column(Date, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    population: Mapped[Population] = mapped_column(Enum(Population), nullable=False)
    margin_of_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    undecided_pct: Mapped[float] = mapped_column(Float, default=0.0)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    race: Mapped["Race"] = relationship(back_populates="polls")
    results: Mapped[list["PollResult"]] = relationship(
        back_populates="poll", cascade="all, delete-orphan"
    )


class PollResult(Base):
    __tablename__ = "poll_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey("polls.id"), nullable=False)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    pct: Mapped[float] = mapped_column(Float, nullable=False)

    poll: Mapped["Poll"] = relationship(back_populates="results")
    candidate: Mapped["Candidate"] = relationship(back_populates="poll_results")


class ForecastSnapshot(Base):
    __tablename__ = "forecast_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    method_version: Mapped[str] = mapped_column(String(40), default="mvp-v1")
    n_simulations: Mapped[int] = mapped_column(Integer, nullable=False)
    n_polls_used: Mapped[int] = mapped_column(Integer, nullable=False)
    poll_weight_alpha: Mapped[float] = mapped_column(Float, nullable=False)
    fundamentals_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)

    race: Mapped["Race"] = relationship(back_populates="forecast_snapshots")
    results: Mapped[list["ForecastResult"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


class ForecastResult(Base):
    __tablename__ = "forecast_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("forecast_snapshots.id"), nullable=False)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False)

    mean_vote_share: Mapped[float] = mapped_column(Float, nullable=False)
    median_vote_share: Mapped[float] = mapped_column(Float, nullable=False)
    std_dev: Mapped[float] = mapped_column(Float, nullable=False)
    win_probability: Mapped[float] = mapped_column(Float, nullable=False)
    ci_low: Mapped[float] = mapped_column(Float, nullable=False)
    ci_high: Mapped[float] = mapped_column(Float, nullable=False)
    # capped sample of Monte Carlo draws for this candidate, used to render histograms
    draws_sample: Mapped[list] = mapped_column(JSON, default=list)
    # pre-blend components, kept for transparency in the "model composition" UI
    polling_vote_share: Mapped[float] = mapped_column(Float, nullable=False)
    fundamentals_vote_share: Mapped[float] = mapped_column(Float, nullable=False)

    snapshot: Mapped["ForecastSnapshot"] = relationship(back_populates="results")
    candidate: Mapped["Candidate"] = relationship(back_populates="forecast_results")


class PresidentApproval(Base):
    """Current sitting president's approval rating, feeding the fundamentals
    model's national-environment adjustment. National, not race-scoped — the
    same row feeds every state's forecast. Seeded from the static default in
    app.data.fundamentals_data at startup, then kept current by the scheduled
    scraper (see app.ingestion.approval_scraper). Single current row —
    refreshes update it in place rather than accumulating a full history."""

    __tablename__ = "president_approval"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    party: Mapped[str] = mapped_column(String(40), nullable=False)
    approval_pct: Mapped[float] = mapped_column(Float, nullable=False)
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class ActualResult(Base):
    """Certified final vote share, populated after the election. Empty until
    then — the forecast-history chart overlays this once it exists."""

    __tablename__ = "actual_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    vote_pct: Mapped[float] = mapped_column(Float, nullable=False)
    certified_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)

    candidate: Mapped["Candidate"] = relationship()
