"""Custom Strands tools for user notifications and deadline monitoring."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests
from backend.config import config
from backend.storage.local_storage import storage

logger = logging.getLogger(__name__)


def send_deadline_alert(
    grant_id: str,
    grant_title: str,
    deadline: str,
    days_remaining: int,
    urgency_level: str = "normal",
) -> dict[str, Any]:
    """Record and surface an upcoming grant application deadline alert.

    Use this tool to notify the user and update the activity timeline when a
    monitored grant deadline is approaching (e.g. 30, 14, 7, 3, or 1 day left).

    Args:
        grant_id: The ID of the grant opportunity.
        grant_title: Official title of the grant.
        deadline: The deadline date string.
        days_remaining: Estimated days until close date.
        urgency_level: 'low', 'normal', 'high', or 'critical'.

    Returns:
        Confirmation dictionary with timestamp and alert status.
    """
    try:
        msg = f"⏳ Deadline Alert: '{grant_title}' closes in {days_remaining} day(s) ({deadline}). Urgency: {urgency_level.upper()}"
        
        storage.add_activity({
            "event_type": "deadline_reminder",
            "message": msg,
            "details": {
                "grant_id": grant_id,
                "grant_title": grant_title,
                "deadline": deadline,
                "days_remaining": days_remaining,
                "urgency": urgency_level,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        logger.info(f"Recorded deadline alert for {grant_id} ({days_remaining} days left)")
        return {
            "delivered": True,
            "grant_id": grant_id,
            "days_remaining": days_remaining,
            "error": None,
        }
    except Exception as e:
        logger.error(f"Failed to record deadline alert: {e}")
        return {"delivered": False, "error": str(e)}


def send_external_notification(
    channel: str,
    subject: str,
    body: str,
    urgency: str = "normal"
) -> dict:
    """Send a notification to external channels (Slack webhook, email).
    
    Args:
        channel: Notification channel ('slack', 'email', 'dashboard').
        subject: Alert subject line.
        body: Full notification text.
        urgency: 'critical', 'high', 'normal', or 'low'.
    
    Returns:
        Delivery confirmation.
    """
    if channel == "slack" and config.SLACK_WEBHOOK_URL:
        emoji = {"critical": "🚨", "high": "⚠️", "normal": "📋", "low": "📌"}
        payload = {
            "text": f"{emoji.get(urgency, '📋')} *{subject}*\n{body}"
        }
        try:
            requests.post(config.SLACK_WEBHOOK_URL, json=payload, timeout=10)
            return {"delivered": True, "channel": "slack"}
        except Exception as e:
            return {"delivered": False, "error": str(e)}
    
    # Default: dashboard-only
    return {"delivered": True, "channel": "dashboard"}


def scan_upcoming_deadlines() -> dict[str, Any]:
    """Scan all active grants in the pipeline and identify upcoming deadlines.

    Use this tool to find grants with active deadlines and prioritize which ones
    require immediate application drafting or submission review.

    Returns:
        List of grants with calculated days remaining and urgency status.
    """
    try:
        grants = storage.list_grants()
        active_deadlines = []

        for g in grants:
            if g.get("status") in ("archived", "submitted"):
                continue
            
            close = g.get("close_date")
            if not close:
                continue

            # Parse date
            days_left = None
            for fmt in ["%Y-%m-%d", "%b %d, %Y", "%m/%d/%Y", "%B %d, %Y"]:
                try:
                    close_clean = close.split(" ")[0] if " " in close and "-" in close else close.split(" 12:")[0]
                    close_dt = datetime.strptime(close_clean, fmt)
                    days_left = (close_dt - datetime.now(timezone.utc)).days
                    break
                except Exception:
                    continue

            if days_left is not None:
                urgency = "low"
                if days_left <= 3:
                    urgency = "critical"
                elif days_left <= 7:
                    urgency = "high"
                elif days_left <= 14:
                    urgency = "normal"

                active_deadlines.append({
                    "grant_id": g.get("grant_id"),
                    "title": g.get("title"),
                    "deadline": close,
                    "days_remaining": days_left,
                    "urgency": urgency,
                    "status": g.get("status"),
                })

        active_deadlines.sort(key=lambda x: x["days_remaining"])
        return {
            "count": len(active_deadlines),
            "deadlines": active_deadlines,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Error scanning deadlines: {e}")
        return {"count": 0, "deadlines": [], "error": str(e)}
