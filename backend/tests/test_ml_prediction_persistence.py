"""Phase 2.2: PredictionOutcome persistence + training loop + regulatory monitor."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models  # noqa: F401
from app.db.session import Base
from app.services import ml_prediction, regulatory_monitor


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _seed_outcome(db, **kwargs):
    row = models.PredictionOutcome(
        id=kwargs.pop("id", f"po_{len(db.query(models.PredictionOutcome).all())}"),
        prediction_id=kwargs.pop("prediction_id", "pred_1"),
        jurisdiction=kwargs.pop("jurisdiction", "TX"),
        model_used=kwargs.pop("model_used", "rules"),
        input_features=kwargs.pop("input_features", {"jurisdiction": "TX"}),
        predicted_settlement=kwargs.pop("predicted_settlement", 100_000),
        actual_settlement=kwargs.pop("actual_settlement", 110_000),
        outcome_date=kwargs.pop("outcome_date", datetime.utcnow()),
        days_to_settlement=kwargs.pop("days_to_settlement", 30),
    )
    for k, v in kwargs.items():
        setattr(row, k, v)
    db.add(row)
    db.commit()
    return row


def test_record_prediction_outcome_persists_to_db(db_session):
    outcome_id = asyncio.run(
        ml_prediction.record_prediction_outcome(
            prediction_id="p1",
            actual_settlement=125_000,
            outcome_date=datetime.utcnow(),
            db=db_session,
            input_features={"jurisdiction": "TX"},
            predicted_settlement=110_000,
            predicted_confidence=0.8,
            model_used="rules",
            jurisdiction="TX",
            days_to_settlement=42,
        )
    )
    assert outcome_id is not None

    rows = db_session.query(models.PredictionOutcome).all()
    assert len(rows) == 1
    assert float(rows[0].actual_settlement) == 125_000
    assert rows[0].model_used == "rules"


def test_get_training_data_returns_persisted_rows(db_session):
    for i in range(3):
        _seed_outcome(db_session, id=f"po_{i}", prediction_id=f"pred_{i}")
    records = asyncio.run(
        ml_prediction.get_training_data(jurisdiction="TX", db=db_session)
    )
    assert len(records) == 3
    assert all(r.actual_settlement > 0 for r in records)


def test_training_loop_skips_when_insufficient_data(db_session):
    _seed_outcome(db_session, id="po_only", prediction_id="pred_x")
    result = asyncio.run(
        ml_prediction.run_training_loop(
            db=db_session,
            min_records=10,
        )
    )
    assert result["status"] == "skipped"
    assert result["records_available"] == 1


def test_training_loop_prepares_when_vertex_disabled(db_session):
    for i in range(5):
        _seed_outcome(db_session, id=f"po_{i}", prediction_id=f"pred_{i}")
    result = asyncio.run(
        ml_prediction.run_training_loop(
            db=db_session,
            min_records=5,
        )
    )
    assert result["status"] == "prepared"
    assert result["records"] == 5


def test_calculate_model_accuracy_returns_metrics(db_session):
    now = datetime.utcnow()
    _seed_outcome(
        db_session,
        id="po_a",
        predicted_settlement=100_000,
        actual_settlement=110_000,
        outcome_date=now,
    )
    _seed_outcome(
        db_session,
        id="po_b",
        predicted_settlement=200_000,
        actual_settlement=180_000,
        outcome_date=now - timedelta(days=5),
    )
    metrics = asyncio.run(
        ml_prediction.calculate_model_accuracy(
            model_type="rules", window_days=60, db=db_session
        )
    )
    assert metrics["samples"] == 2
    assert metrics["mae"] == pytest.approx(15_000, rel=1e-6)
    assert metrics["rmse"] > 0


class _FakeFeed:
    def __init__(self, items):
        self._items = items

    async def fetch(self, jurisdiction):
        return [i for i in self._items if i.jurisdiction == jurisdiction]


def test_regulatory_monitor_persists_new_items(db_session):
    item = regulatory_monitor.FeedItem(
        source="TX Legislature",
        source_type="legislature",
        jurisdiction="TX",
        change_type="amendment",
        title="Prop. Code § 21.0113 clarification",
        summary="Requires written bona fide offer.",
        citation="Tex. Prop. Code § 21.0113",
    )
    regulatory_monitor.register_feed("test_feed", _FakeFeed([item]))
    try:
        summary = asyncio.run(
            regulatory_monitor.run_monitor(db_session, ["TX"])
        )
    finally:
        regulatory_monitor._feeds.pop("test_feed", None)

    assert summary["total_created"] == 1
    rows = db_session.query(models.RegulatoryUpdate).all()
    assert len(rows) == 1
    assert rows[0].jurisdiction == "TX"
    assert rows[0].status == "pending"

    # Also verify legacy law_changes mirror populated.
    lc_rows = db_session.query(models.LawChange).all()
    assert len(lc_rows) == 1


def test_regulatory_monitor_dedupes_pending_items(db_session):
    item = regulatory_monitor.FeedItem(
        source="TX Legislature",
        source_type="legislature",
        jurisdiction="TX",
        change_type="amendment",
        title="Dup title",
        summary="...",
        citation="Tex. Prop. Code § 21.0113",
    )
    regulatory_monitor.register_feed("dup_feed", _FakeFeed([item]))
    try:
        first = asyncio.run(regulatory_monitor.run_monitor(db_session, ["TX"]))
        second = asyncio.run(regulatory_monitor.run_monitor(db_session, ["TX"]))
    finally:
        regulatory_monitor._feeds.pop("dup_feed", None)

    assert first["total_created"] == 1
    assert second["total_created"] == 0
    rows = db_session.query(models.RegulatoryUpdate).all()
    assert len(rows) == 1
