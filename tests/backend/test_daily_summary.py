"""Tests for Daily Surveillance Summary Engine and Endpoints."""
import datetime
import pytest
from backend.database import SessionLocal
from backend import models
from backend.summaries.generator import DailySummaryGenerator
from backend.summaries.routes import (
    get_daily_summary,
    generate_daily_summary,
    download_summary_report,
)


def test_daily_summary_generator_logic():
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    with SessionLocal() as db:
        summary = DailySummaryGenerator.get_or_generate_summary(db, today_str, force_regenerate=True)
        assert summary["date"] == today_str
        assert "narrative_summary" in summary
        assert len(summary["narrative_summary"]) > 10
        assert len(summary["timeline_segments"]) == 48
        assert len(summary["hourly_distribution"]) == 24


def test_daily_summary_route_functions():
    with SessionLocal() as db:
        admin = db.query(models.User).filter(models.User.email == "admin@cctv.local").first()
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")

        # 1. get_daily_summary
        summary = get_daily_summary(date=today_str, db=db, current_user=admin)
        assert summary["date"] == today_str
        assert "narrative_summary" in summary

        # 2. generate_daily_summary
        gen_res = generate_daily_summary(date=today_str, db=db, current_user=admin)
        assert gen_res["date"] == today_str

        # 3. download_summary_report
        resp = download_summary_report(date=today_str, db=db, current_user=admin)
        content_text = resp.body.decode()
        assert "CCTV Intelligence — Daily Surveillance Report" in content_text
        assert today_str in content_text
