"""Automated Daily Surveillance Summary Engine.
Calculates deterministic surveillance metrics, 24-hour timeline, hourly distributions,
and generates human-readable natural language daily surveillance narratives.
"""
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from backend import models
from backend.config import settings


class DailySummaryGenerator:
    """Calculates and persists daily surveillance summaries from database events."""

    @staticmethod
    def get_or_generate_summary(
        db: Session,
        date_str: str,
        force_regenerate: bool = False,
    ) -> Dict[str, Any]:
        """
        Retrieves or calculates surveillance summary for a specific date (YYYY-MM-DD).
        If date is today, always recalculates live metrics from active database events.
        """
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        is_today = (date_str == today_str)

        # Parse target date
        try:
            target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = datetime.datetime.now().date()
            date_str = target_date.strftime("%Y-%m-%d")

        start_dt = datetime.datetime.combine(target_date, datetime.time.min)
        end_dt = datetime.datetime.combine(target_date, datetime.time.max)

        # 1. Fetch Motion Events for this date
        events = (
            db.query(models.MotionEvent)
            .filter(
                models.MotionEvent.start_time >= start_dt,
                models.MotionEvent.start_time <= end_dt,
            )
            .order_by(models.MotionEvent.start_time.asc())
            .all()
        )

        # 2. Fetch Sessions for this date
        sessions = (
            db.query(models.MonitoringSession)
            .filter(
                models.MonitoringSession.start_time >= start_dt,
                models.MonitoringSession.start_time <= end_dt,
            )
            .all()
        )

        # 3. Fetch Captured Frames count
        frames_saved_count = (
            db.query(func.count(models.CapturedFrame.id))
            .filter(
                models.CapturedFrame.timestamp >= start_dt,
                models.CapturedFrame.timestamp <= end_dt,
            )
            .scalar()
            or 0
        )

        # 4. Fetch Recordings
        recordings = (
            db.query(models.Recording)
            .filter(
                models.Recording.start_time >= start_dt,
                models.Recording.start_time <= end_dt,
            )
            .all()
        )

        # Compute durations
        total_monitoring_sec = sum(
            (
                (s.end_time - s.start_time).total_seconds()
                if s.end_time
                else (datetime.datetime.now() - s.start_time).total_seconds()
            )
            for s in sessions
        )
        active_sec = sum(s.active_duration_seconds or 0.0 for s in sessions)
        idle_sec = sum(s.idle_duration_seconds or 0.0 for s in sessions)
        deep_idle_sec = sum(s.deep_idle_duration_seconds or 0.0 for s in sessions)
        total_frames_captured = sum(s.total_frames or 0 for s in sessions)

        # If live camera is currently running today, incorporate live durations
        from vision.camera_manager import camera_manager
        if is_today and camera_manager.is_monitoring:
            status = camera_manager.get_status()
            active_sec = max(active_sec, status["active_seconds"])
            idle_sec = max(idle_sec, status["idle_seconds"])
            deep_idle_sec = max(deep_idle_sec, status["deep_idle_seconds"])
            total_monitoring_sec = max(total_monitoring_sec, status["uptime_seconds"])
            total_frames_captured = max(total_frames_captured, status["total_frames_processed"])
            frames_saved_count = max(frames_saved_count, status["total_frames_saved"])

        # Compute storage consumed
        storage_bytes = sum(r.file_size_bytes or 0 for r in recordings)
        # Approximate frame storage: 50 KB per frame
        storage_bytes += frames_saved_count * 50 * 1024

        total_motion_events = len(events)
        first_activity = events[0].start_time if events else None
        last_activity = events[-1].start_time if events else None

        # 5. Build Hourly Distribution (24 hours)
        hourly_distribution = []
        hourly_counts = [0] * 24
        hourly_active_mins = [0.0] * 24

        for ev in events:
            hour = ev.start_time.hour
            hourly_counts[hour] += 1
            duration = (
                (ev.end_time - ev.start_time).total_seconds()
                if ev.end_time
                else 10.0
            )
            hourly_active_mins[hour] += duration / 60.0

        for h in range(24):
            hourly_distribution.append({
                "hour": h,
                "label": f"{h:02d}:00",
                "event_count": hourly_counts[h],
                "active_minutes": round(hourly_active_mins[h], 1),
            })

        # Determine Peak Activity Hour
        peak_hour = None
        if total_motion_events > 0:
            peak_hour = max(range(24), key=lambda h: (hourly_counts[h], hourly_active_mins[h]))

        # 6. Build 24-Hour Timeline Segments
        timeline_segments = DailySummaryGenerator._build_timeline_segments(
            start_dt, end_dt, sessions, events
        )

        # 7. Generate Natural Language Surveillance Narrative
        narrative = DailySummaryGenerator._synthesize_narrative(
            date_str=date_str,
            sessions=sessions,
            events=events,
            total_monitoring_sec=total_monitoring_sec,
            active_sec=active_sec,
            idle_sec=idle_sec,
            deep_idle_sec=deep_idle_sec,
            total_motion_events=total_motion_events,
            peak_hour=peak_hour,
            first_activity=first_activity,
            last_activity=last_activity,
            frames_saved=frames_saved_count,
            storage_bytes=storage_bytes,
        )

        # 8. Upsert in DB daily_summaries table
        summary_rec = db.query(models.DailySummary).filter(models.DailySummary.date == date_str).first()
        if not summary_rec:
            summary_rec = models.DailySummary(date=date_str)
            db.add(summary_rec)

        summary_rec.total_monitoring_seconds = round(total_monitoring_sec, 2)
        summary_rec.active_seconds = round(active_sec, 2)
        summary_rec.idle_seconds = round(idle_sec, 2)
        summary_rec.deep_idle_seconds = round(deep_idle_sec, 2)
        summary_rec.total_motion_events = total_motion_events
        summary_rec.total_frames_captured = total_frames_captured
        summary_rec.total_frames_saved = frames_saved_count
        summary_rec.storage_consumed_bytes = storage_bytes
        summary_rec.first_activity_time = first_activity
        summary_rec.last_activity_time = last_activity
        summary_rec.peak_activity_hour = peak_hour
        summary_rec.narrative_summary = narrative
        db.commit()
        db.refresh(summary_rec)

        # 9. Top Important Events (up to 10 most prominent)
        sorted_events = sorted(
            events,
            key=lambda e: (e.peak_motion_score or 0.0, e.frame_count or 0),
            reverse=True,
        )[:10]

        important_events_out = [
            {
                "id": ev.id,
                "camera_id": ev.camera_id,
                "session_id": ev.session_id,
                "start_time": ev.start_time,
                "end_time": ev.end_time,
                "peak_motion_score": ev.peak_motion_score or 0.0,
                "activity_state": ev.activity_state,
                "frame_count": ev.frame_count or 0,
                "thumbnail_path": ev.thumbnail_path,
                "description": ev.description,
            }
            for ev in sorted_events
        ]

        return {
            "id": summary_rec.id,
            "date": date_str,
            "total_monitoring_seconds": round(total_monitoring_sec, 2),
            "active_seconds": round(active_sec, 2),
            "idle_seconds": round(idle_sec, 2),
            "deep_idle_seconds": round(deep_idle_sec, 2),
            "total_motion_events": total_motion_events,
            "total_frames_captured": total_frames_captured,
            "total_frames_saved": frames_saved_count,
            "storage_consumed_bytes": storage_bytes,
            "first_activity_time": first_activity,
            "last_activity_time": last_activity,
            "peak_activity_hour": peak_hour,
            "narrative_summary": narrative,
            "timeline_segments": timeline_segments,
            "hourly_distribution": hourly_distribution,
            "important_events": important_events_out,
        }

    @staticmethod
    def _build_timeline_segments(
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
        sessions: List[models.MonitoringSession],
        events: List[models.MotionEvent],
    ) -> List[Dict[str, Any]]:
        """Construct structured 24-hour timeline blocks with activity classification."""
        segments = []
        # Divide the 24 hours into 48 half-hour windows for granular visualization
        step = datetime.timedelta(minutes=30)
        curr = start_dt

        while curr < end_dt:
            next_curr = min(curr + step, end_dt)

            # Check if any session was running during this window
            has_session = any(
                (s.start_time <= next_curr and (s.end_time is None or s.end_time >= curr))
                for s in sessions
            )

            # Check events in this window
            window_events = [
                e for e in events
                if (e.start_time >= curr and e.start_time < next_curr)
            ]

            if not has_session and not window_events:
                state = "OFFLINE"
            elif len(window_events) > 0:
                state = "ACTIVE"
            else:
                state = "IDLE"

            segments.append({
                "start_time": curr.strftime("%H:%M"),
                "end_time": next_curr.strftime("%H:%M"),
                "activity_state": state,
                "duration_seconds": (next_curr - curr).total_seconds(),
                "event_count": len(window_events),
            })
            curr = next_curr

        return segments

    @staticmethod
    def _synthesize_narrative(
        date_str: str,
        sessions: List[models.MonitoringSession],
        events: List[models.MotionEvent],
        total_monitoring_sec: float,
        active_sec: float,
        idle_sec: float,
        deep_idle_sec: float,
        total_motion_events: int,
        peak_hour: Optional[int],
        first_activity: Optional[datetime.datetime],
        last_activity: Optional[datetime.datetime],
        frames_saved: int,
        storage_bytes: int,
    ) -> str:
        """Generate fluent, accurate surveillance narrative using calculated database data."""
        mb_storage = storage_bytes / (1024 * 1024)

        if total_monitoring_sec <= 0:
            return f"No monitoring sessions recorded on {date_str}. The surveillance system remained offline."

        # Format monitoring duration
        hours = int(total_monitoring_sec // 3600)
        mins = int((total_monitoring_sec % 3600) // 60)
        duration_phrase = f"{hours}h {mins}m" if hours > 0 else f"{mins} minutes"

        parts = []

        # Session opening
        if sessions:
            first_session_time = sessions[0].start_time.strftime("%I:%M %p")
            parts.append(
                f"Surveillance monitoring for {date_str} commenced at {first_session_time}, "
                f"accumulating {duration_phrase} of active coverage."
            )
        else:
            parts.append(f"Surveillance operations accumulated {duration_phrase} of active coverage on {date_str}.")

        # Motion activity
        if total_motion_events == 0:
            parts.append("No significant motion events were detected throughout the monitored period.")
        else:
            first_str = first_activity.strftime("%I:%M %p") if first_activity else "N/A"
            last_str = last_activity.strftime("%I:%M %p") if last_activity else "N/A"
            parts.append(
                f"The system recorded {total_motion_events} verified motion event{'s' if total_motion_events != 1 else ''}. "
                f"Initial motion was logged at {first_str}, and final activity was observed at {last_str}."
            )

        # Peak window
        if peak_hour is not None:
            peak_start = f"{peak_hour:02d}:00"
            peak_end = f"{(peak_hour + 1) % 24:02d}:00"
            parts.append(
                f"The highest concentration of motion occurred between {peak_start} and {peak_end}."
            )

        # Activity distribution
        if total_monitoring_sec > 0:
            active_pct = round((active_sec / total_monitoring_sec) * 100.0, 1)
            idle_pct = round(((idle_sec + deep_idle_sec) / total_monitoring_sec) * 100.0, 1)
            parts.append(
                f"Activity breakdown: {active_pct}% in ACTIVE state, with the camera remaining IDLE or DEEP IDLE for {idle_pct}% of the duration."
            )

        # Storage & Adaptive sampling
        parts.append(
            f"Adaptive frame sampling persisted {frames_saved:,} priority frames to storage ({mb_storage:.1f} MB utilized)."
        )

        return " ".join(parts)
