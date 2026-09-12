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
    grant_title: str = "",
    deadline: str = "",
    days_remaining: int = 0,
    urgency_level: str = "normal",
    priority: str = "",
    **kwargs: Any,
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
        priority: Alias for urgency_level.

    Returns:
        Confirmation dictionary with timestamp and alert status.
    """
    try:
        urgency = priority or urgency_level or "normal"
        if not grant_title or not deadline:
            grant = storage.get_grant(grant_id)
            if grant:
                grant_title = grant_title or grant.get("title", f"Grant {grant_id}")
                deadline = deadline or grant.get("close_date", "Upcoming")
            else:
                grant_title = grant_title or f"Grant {grant_id}"
                deadline = deadline or "Upcoming"

        msg = f"⏳ Deadline Alert: '{grant_title}' closes in {days_remaining} day(s) ({deadline}). Urgency: {urgency.upper()}"
        
        storage.add_activity({
            "event_type": "deadline_reminder",
            "message": msg,
            "details": {
                "grant_id": grant_id,
                "grant_title": grant_title,
                "deadline": deadline,
                "days_remaining": days_remaining,
                "urgency": urgency,
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
    subject: str = "GrantScout Notification",
    body: str = "",
    message: str = "",
    urgency: str = "normal",
    **kwargs: Any,
) -> dict[str, Any]:
    """Send a notification to external channels (Slack webhook, email).
    
    Args:
        channel: Notification channel ('slack', 'email', 'dashboard').
        subject: Alert subject line.
        body: Full notification text.
        message: Optional alias for body text.
        urgency: 'critical', 'high', 'normal', or 'low'.
    
    Returns:
        Delivery confirmation.
    """
    body_text = body or message or subject
    if channel == "slack" and config.SLACK_WEBHOOK_URL:
        emoji = {"critical": "🚨", "high": "⚠️", "normal": "📋", "low": "📌"}
        payload = {
            "text": f"{emoji.get(urgency, '📋')} *{subject}*\n{body_text}"
        }
        try:
            requests.post(config.SLACK_WEBHOOK_URL, json=payload, timeout=10)
            return {"delivered": True, "channel": "slack"}
        except Exception as e:
            return {"delivered": False, "error": str(e)}
    
    # Default: dashboard-only
    return {"delivered": True, "channel": "dashboard"}


def scan_upcoming_deadlines(days_ahead: int = 30, **kwargs: Any) -> dict[str, Any]:
    """Scan all active grants in the pipeline and identify upcoming deadlines.

    Use this tool to find grants with active deadlines and prioritize which ones
    require immediate application drafting or submission review.

    Args:
        days_ahead: Maximum days ahead to inspect (default 30).

    Returns:
        List of grants with calculated days remaining and urgency status.
    """
    try:
        grants = storage.list_grants()
        active_deadlines = []
        now_utc = datetime.now(timezone.utc)

        for g in grants:
            if g.get("status") in ("archived", "submitted"):
                continue
            
            close = g.get("close_date")
            if not close:
                continue

            # Parse date robustly and attach timezone.utc
            days_left = None
            for fmt in ["%Y-%m-%d", "%b %d, %Y", "%m/%d/%Y", "%B %d, %Y"]:
                try:
                    close_clean = close.split(" ")[0] if " " in close and "-" in close else close.split(" 12:")[0]
                    close_dt = datetime.strptime(close_clean, fmt).replace(tzinfo=timezone.utc)
                    days_left = (close_dt - now_utc).days
                    break
                except Exception:
                    continue

            if days_left is not None:
                # Include upcoming deadlines within days_ahead (or all positive if window is large)
                if days_left <= days_ahead:
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
