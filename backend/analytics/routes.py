"""Surveillance analytics and historical trends endpoints."""
import datetime
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import get_db
from backend import models, schemas
from backend.auth.routes import get_current_user
from backend.config import settings
from vision.camera_manager import camera_manager

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/overview", response_model=schemas.AnalyticsOverviewOut)
def get_analytics_overview(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieve top-level KPI analytics for today and the past week scoped to user."""
    today = datetime.datetime.now().date()
    today_start = datetime.datetime.combine(today, datetime.time.min)
    today_end = datetime.datetime.combine(today, datetime.time.max)
    week_start = today_start - datetime.timedelta(days=7)

    # Scoped event query
    ev_q = db.query(func.count(models.MotionEvent.id)).filter(
        models.MotionEvent.start_time >= today_start,
        models.MotionEvent.start_time <= today_end,
    )
    if current_user.role != "admin":
        ev_q = ev_q.filter(models.MotionEvent.user_id == current_user.id)
    events_today_count = ev_q.scalar() or 0

    # Scoped recordings count & bytes
    rec_q = db.query(models.Recording)
    if current_user.role != "admin":
        rec_q = rec_q.filter(models.Recording.user_id == current_user.id)
    recordings = rec_q.all()
    recordings_count = len(recordings)
    total_rec_bytes = sum(r.file_size_bytes or 0 for r in recordings)

    # Scoped frames
    frame_q = db.query(models.CapturedFrame)
    if current_user.role != "admin":
        frame_q = frame_q.filter(models.CapturedFrame.user_id == current_user.id)
    frames = frame_q.all()
    total_frame_bytes = sum(f.file_size_bytes or 0 for f in frames)
    total_storage = total_rec_bytes + total_frame_bytes

    # Sessions today
    sess_q = db.query(models.MonitoringSession).filter(
        models.MonitoringSession.start_time >= today_start,
        models.MonitoringSession.start_time <= today_end,
    )
    if current_user.role != "admin":
        sess_q = sess_q.filter(models.MonitoringSession.user_id == current_user.id)
    sessions_today = sess_q.all()

    active_sec = sum(s.active_duration_seconds or 0.0 for s in sessions_today if s.status == "completed")
    idle_sec = sum(s.idle_duration_seconds or 0.0 for s in sessions_today if s.status == "completed")
    deep_idle_sec = sum(s.deep_idle_duration_seconds or 0.0 for s in sessions_today if s.status == "completed")

    # Add live telemetry additively if user owns session or is admin
    if camera_manager.is_monitoring and (current_user.role == "admin" or camera_manager.user_id == current_user.id or camera_manager.user_id is None):
        cam_status = camera_manager.get_status()
        active_sec += cam_status["active_seconds"]
        idle_sec += cam_status["idle_seconds"]
        deep_idle_sec += cam_status["deep_idle_seconds"]

    total_monitored_today = active_sec + idle_sec + deep_idle_sec
    active_ratio = round((active_sec / total_monitored_today) * 100.0, 1) if total_monitored_today > 0 else 0.0

    # Monitoring hours this week
    week_q = db.query(models.MonitoringSession).filter(models.MonitoringSession.start_time >= week_start)
    if current_user.role != "admin":
        week_q = week_q.filter(models.MonitoringSession.user_id == current_user.id)
    sessions_week = week_q.all()

    week_seconds = sum(
        (
            (s.end_time - s.start_time).total_seconds()
            if s.end_time
            else (datetime.datetime.now() - s.start_time).total_seconds()
        )
        for s in sessions_week
    )
    if camera_manager.is_monitoring and (current_user.role == "admin" or camera_manager.user_id == current_user.id or camera_manager.user_id is None):
        week_seconds += camera_manager.get_status()["uptime_seconds"]

    return {
        "today_active_seconds": round(active_sec, 1),
        "today_idle_seconds": round(idle_sec, 1),
        "today_deep_idle_seconds": round(deep_idle_sec, 1),
        "total_motion_events_today": events_today_count,
        "total_recordings_count": recordings_count,
        "total_storage_used_bytes": total_storage,
        "total_monitoring_hours_week": round(week_seconds / 3600.0, 2),
        "active_ratio_today": active_ratio,
    }


@router.get("/trends", response_model=schemas.AnalyticsTrendsOut)
def get_analytics_trends(
    days: int = Query(7, ge=3, le=30),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieve historical surveillance activity trends across past N days."""
    today = datetime.datetime.now().date()
    dates_list = []
    active_durations = []
    idle_durations = []
    deep_idle_durations = []
    event_counts = []
    storage_trends = []

    cumulative_storage = 0

    for i in range(days - 1, -1, -1):
        target_date = today - datetime.timedelta(days=i)
        date_str = target_date.strftime("%Y-%m-%d")
        dates_list.append(date_str)

        start_dt = datetime.datetime.combine(target_date, datetime.time.min)
        end_dt = datetime.datetime.combine(target_date, datetime.time.max)

        # Check existing summary first scoped to user
        summary_q = db.query(models.DailySummary).filter(models.DailySummary.date == date_str)
        if current_user.role != "admin":
            summary_q = summary_q.filter(models.DailySummary.user_id == current_user.id)
        summary = summary_q.first()

        if summary:
            active_durations.append(round(summary.active_seconds / 60.0, 1))
            idle_durations.append(round(summary.idle_seconds / 60.0, 1))
            deep_idle_durations.append(round(summary.deep_idle_seconds / 60.0, 1))
            event_counts.append(summary.total_motion_events)
            cumulative_storage += summary.storage_consumed_bytes
            storage_trends.append(cumulative_storage)
        else:
            # Query sessions & events directly scoped to user
            sess_q = db.query(models.MonitoringSession).filter(
                models.MonitoringSession.start_time <= end_dt,
                (models.MonitoringSession.end_time == None) | (models.MonitoringSession.end_time >= start_dt),
            )
            ev_q = db.query(func.count(models.MotionEvent.id)).filter(
                models.MotionEvent.start_time >= start_dt,
                models.MotionEvent.start_time <= end_dt,
            )
            if current_user.role != "admin":
                sess_q = sess_q.filter(models.MonitoringSession.user_id == current_user.id)
                ev_q = ev_q.filter(models.MotionEvent.user_id == current_user.id)

            sessions = sess_q.all()
            ev_count = ev_q.scalar() or 0

            a_sec = sum(s.active_duration_seconds or 0 for s in sessions if s.status == "completed")
            i_sec = sum(s.idle_duration_seconds or 0 for s in sessions if s.status == "completed")
            d_sec = sum(s.deep_idle_duration_seconds or 0 for s in sessions if s.status == "completed")

            if target_date == today and camera_manager.is_monitoring and (current_user.role == "admin" or camera_manager.user_id == current_user.id or camera_manager.user_id is None):
                status = camera_manager.get_status()
                a_sec += status["active_seconds"]
                i_sec += status["idle_seconds"]
                d_sec += status["deep_idle_seconds"]

            active_durations.append(round(a_sec / 60.0, 1))
            idle_durations.append(round(i_sec / 60.0, 1))
            deep_idle_durations.append(round(d_sec / 60.0, 1))
            event_counts.append(ev_count)
            cumulative_storage += ev_count * 1024 * 1024
            storage_trends.append(cumulative_storage)

    return {
        "dates": dates_list,
        "active_durations": active_durations,
        "idle_durations": idle_durations,
        "deep_idle_durations": deep_idle_durations,
        "motion_event_counts": event_counts,
        "storage_trend_bytes": storage_trends,
    }
