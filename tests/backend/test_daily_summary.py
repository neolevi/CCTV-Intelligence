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
    get_available_summary_dates,
)
from backend.events.routes import get_event_thumbnail
from pathlib import Path


def test_daily_summary_generator_logic():
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    with SessionLocal() as db:
        summary = DailySummaryGenerator.get_or_generate_summary(db, today_str, force_regenerate=True)
        assert summary["date"] == today_str
        assert "narrative_summary" in summary
        assert len(summary["narrative_summary"]) > 10
        assert len(summary["timeline_segments"]) == 48
        assert len(summary["hourly_distribution"]) == 24
        assert "events" in summary
        assert "important_events" in summary


def test_daily_summary_route_functions():
    with SessionLocal() as db:
        admin = db.query(models.User).filter(models.User.email == "admin@cctv.local").first()
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")

        # 1. get_daily_summary
        summary = get_daily_summary(date=today_str, db=db, current_user=admin)
        assert summary["date"] == today_str
        assert "narrative_summary" in summary
        assert "events" in summary

        # 2. generate_daily_summary
        gen_res = generate_daily_summary(date=today_str, db=db, current_user=admin)
        assert gen_res["date"] == today_str
        assert "events" in gen_res

        # 3. download_summary_report
        resp = download_summary_report(date=today_str, db=db, current_user=admin)
        content_text = resp.body.decode()
        assert "CCTV Intelligence — Daily Surveillance Report" in content_text
        assert today_str in content_text


def test_daily_summary_shows_event_images_and_timestamps():
    """Ensure Daily Summary includes all events with images and timestamps for that day."""
    test_date_str = "2026-04-12"
    ev_time = datetime.datetime(2026, 4, 12, 14, 30, 0)
    with SessionLocal() as db:
        admin = db.query(models.User).filter(models.User.email == "admin@cctv.local").first()
        assert admin is not None

        # Clean any existing records on that date
        db.query(models.DailySummary).filter(models.DailySummary.date == test_date_str).delete()
        db.query(models.MotionEvent).filter(models.MotionEvent.start_time >= datetime.datetime(2026, 4, 12, 0, 0, 0),
                                            models.MotionEvent.start_time < datetime.datetime(2026, 4, 13, 0, 0, 0)).delete()
        db.commit()

        # Insert motion event with thumbnail image and timestamp
        ev = models.MotionEvent(
            camera_id=1,
            user_id=admin.id,
            start_time=ev_time,
            end_time=ev_time + datetime.timedelta(seconds=25),
            activity_state="ACTIVE",
            peak_motion_score=88.5,
            frame_count=15,
            thumbnail_path="C:/surveillance/thumbnails/2026-04-12/thumb_test.jpg",
            description="Front Entrance Motion",
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)

        # Generate summary
        summary = get_daily_summary(date=test_date_str, db=db, current_user=admin)
        assert summary["date"] == test_date_str
        assert summary["total_motion_events"] == 1
        assert len(summary["events"]) >= 1

        first_event = summary["events"][0]
        assert first_event["id"] == ev.id
        assert first_event["thumbnail_path"] == "C:/surveillance/thumbnails/2026-04-12/thumb_test.jpg"
        assert first_event["start_time"] == ev_time
        assert first_event["peak_motion_score"] == 88.5

        # Cleanup
        db.delete(ev)
        db.query(models.DailySummary).filter(models.DailySummary.date == test_date_str).delete()
        db.commit()


def test_daily_summary_available_dates_history_navigation():
    """Ensure the user can list and select previous days summaries."""
    past_date_str = "2026-03-25"
    with SessionLocal() as db:
        admin = db.query(models.User).filter(models.User.email == "admin@cctv.local").first()
        assert admin is not None

        # Add a summary for a past date
        ds = models.DailySummary(
            user_id=admin.id,
            date=past_date_str,
            total_monitoring_seconds=3600.0,
            active_seconds=450.0,
            idle_seconds=3150.0,
            deep_idle_seconds=0.0,
            total_motion_events=3,
            storage_consumed_bytes=2048576,
        )
        db.add(ds)
        db.commit()

        # Call get_available_summary_dates
        dates_list = get_available_summary_dates(db=db, current_user=admin)
        assert isinstance(dates_list, list)
        assert len(dates_list) > 0

        # Verify past date is in the list with correct metadata
        matching = [d for d in dates_list if d["date"] == past_date_str]
        assert len(matching) == 1
        item = matching[0]
        assert item["date"] == past_date_str
        assert item["total_events"] == 3
        assert item["has_summary"] is True
        assert item["active_seconds"] == 450.0

        # Verify dates are sorted descending (newest first)
        date_strings = [d["date"] for d in dates_list]
        assert date_strings == sorted(date_strings, reverse=True)

        # Cleanup
        db.delete(ds)
        db.commit()


def test_event_thumbnail_fallback_to_captured_frame(tmp_path):
    """Ensure get_event_thumbnail falls back to first captured frame if thumbnail file is missing."""
    with SessionLocal() as db:
        admin = db.query(models.User).filter(models.User.email == "admin@cctv.local").first()
        assert admin is not None

        # Create dummy frame image file on disk
        frame_file = tmp_path / "frame_fallback.jpg"
        frame_file.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb")

        # Create event with missing thumbnail
        ev = models.MotionEvent(
            camera_id=1,
            user_id=admin.id,
            start_time=datetime.datetime.now(),
            activity_state="ACTIVE",
            peak_motion_score=75.0,
            frame_count=1,
            thumbnail_path="C:/nonexistent/missing_thumb.jpg",
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)

        # Create captured frame referencing this event
        cf = models.CapturedFrame(
            camera_id=1,
            user_id=admin.id,
            event_id=ev.id,
            timestamp=datetime.datetime.now(),
            activity_state="ACTIVE",
            file_path=str(frame_file),
            motion_score=75.0,
            file_size_bytes=len(frame_file.read_bytes()),
        )
        db.add(cf)
        db.commit()

        # Call get_event_thumbnail -> should fall back and serve frame_file
        resp = get_event_thumbnail(event_id=ev.id, db=db, current_user=admin)
        assert resp.status_code == 200
        assert resp.path == str(frame_file)

        # Cleanup
        db.delete(cf)
        db.delete(ev)
        db.commit()
