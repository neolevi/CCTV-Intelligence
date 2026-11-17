"""Daily Surveillance Summary API routes."""
import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models, schemas
from backend.auth.routes import get_current_user, get_current_user_flexible
from backend.summaries.generator import DailySummaryGenerator

router = APIRouter(prefix="/api/summaries", tags=["Daily Summaries"])


def validate_date_param(date_str: Optional[str]) -> str:
    """Validate that date_str is formatted as YYYY-MM-DD, or return today's date."""
    if not date_str:
        return datetime.datetime.now().strftime("%Y-%m-%d")
    try:
        parsed = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return parsed.strftime("%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Expected YYYY-MM-DD",
        )


@router.get("/daily", response_model=schemas.DailySummaryOut)
def get_daily_summary(
    date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieve today's surveillance summary or for a specified date."""
    valid_date = validate_date_param(date)

    summary_data = DailySummaryGenerator.get_or_generate_summary(
        db=db,
        date_str=valid_date,
        force_regenerate=False,
    )
    return summary_data


@router.get("/daily/{date}", response_model=schemas.DailySummaryOut)
def get_daily_summary_by_date(
    date: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieve daily summary by specific date (YYYY-MM-DD)."""
    valid_date = validate_date_param(date)
    summary_data = DailySummaryGenerator.get_or_generate_summary(
        db=db,
        date_str=valid_date,
        force_regenerate=False,
    )
    return summary_data


@router.post("/generate/{date}", response_model=schemas.DailySummaryOut)
def generate_daily_summary(
    date: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Trigger on-demand recalculation and persistence of daily surveillance summary."""
    valid_date = validate_date_param(date)
    summary_data = DailySummaryGenerator.get_or_generate_summary(
        db=db,
        date_str=valid_date,
        force_regenerate=True,
    )
    return summary_data


@router.get("/{date}/download")
def download_summary_report(
    date: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_flexible),
):
    """Download comprehensive daily surveillance report in formatted Markdown text."""
    valid_date = validate_date_param(date)
    summary_data = DailySummaryGenerator.get_or_generate_summary(
        db=db,
        date_str=valid_date,
        force_regenerate=False,
    )

    first_act_str = summary_data["first_activity_time"].strftime("%I:%M:%S %p") if summary_data["first_activity_time"] else "None"
    last_act_str = summary_data["last_activity_time"].strftime("%I:%M:%S %p") if summary_data["last_activity_time"] else "None"
    peak_str = f"{summary_data['peak_activity_hour']:02d}:00" if summary_data["peak_activity_hour"] is not None else "N/A"
    storage_mb = summary_data["storage_consumed_bytes"] / (1024 * 1024)

    report = f"""# CCTV Intelligence — Daily Surveillance Report
**Date:** {summary_data['date']}
**Generated At:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 1. Executive Summary Narrative
{summary_data['narrative_summary']}

---

## 2. Key Surveillance Metrics
- **Total Monitoring Duration:** {summary_data['total_monitoring_seconds']:.1f} seconds ({summary_data['total_monitoring_seconds'] / 3600.0:.2f} hours)
- **Active Duration:** {summary_data['active_seconds']:.1f} seconds
- **Idle Duration:** {summary_data['idle_seconds']:.1f} seconds
- **Deep Idle Duration:** {summary_data['deep_idle_seconds']:.1f} seconds
- **Verified Motion Events:** {summary_data['total_motion_events']}
- **Total Frames Evaluated:** {summary_data['total_frames_captured']:,}
- **Adaptive Frames Persisted:** {summary_data['total_frames_saved']:,}
- **Storage Consumed:** {storage_mb:.2f} MB ({summary_data['storage_consumed_bytes']:,} bytes)
- **First Detected Activity:** {first_act_str}
- **Last Detected Activity:** {last_act_str}
- **Peak Activity Hour:** {peak_str}

---

## 3. Hourly Motion Distribution
| Hour | Label | Motion Events | Active Minutes |
| :--- | :--- | :--- | :--- |
"""
    for h in summary_data["hourly_distribution"]:
        report += f"| {h['hour']:02d} | {h['label']} | {h['event_count']} | {h['active_minutes']:.1f} min |\n"

    report += """
---
*CCTV Intelligence Automated Surveillance Report*
"""

    return Response(
        content=report,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=cctv_summary_{date}.md"},
    )
