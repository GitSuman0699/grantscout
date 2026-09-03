"""Local file-based storage for development without AWS.

Provides the same interface as S3/DynamoDB but stores data
as JSON files on the local filesystem. This allows full
development and testing without AWS credentials.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from backend.config import config

logger = logging.getLogger(__name__)


class LocalStorage:
    """File-based storage backend for local development."""

    def __init__(self, base_path: str = ""):
        self.base_path = Path(base_path or config.LOCAL_STORAGE_PATH)
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create the required directory structure."""
        dirs = [
            self.base_path / "org_profiles",
            self.base_path / "grants",
            self.base_path / "applications",
            self.base_path / "activity",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _serialize(self, obj: Any) -> str:
        """Serialize an object to JSON, handling datetime objects."""

        def default(o: Any) -> str:
            if isinstance(o, datetime):
                return o.isoformat()
            raise TypeError(f"Object of type {type(o)} is not JSON serializable")

        return json.dumps(obj, default=default, indent=2)

    # ── Org Profile Operations ──

    def save_org_profile(self, profile: dict) -> str:
        """Save an organization profile."""
        org_id = profile.get("org_id", "default")
        filepath = self.base_path / "org_profiles" / f"{org_id}.json"
        filepath.write_text(self._serialize(profile), encoding="utf-8")
        logger.info(f"Saved org profile: {org_id}")
        return org_id

    def get_org_profile(self, org_id: str = "default") -> Optional[dict]:
        """Retrieve an organization profile."""
        filepath = self.base_path / "org_profiles" / f"{org_id}.json"
        if filepath.exists():
            return json.loads(filepath.read_text(encoding="utf-8"))
        return None

    # ── Grant Operations ──

    def save_grant(self, grant: dict) -> str:
        """Save a grant opportunity."""
        grant_id = grant.get("grant_id", "unknown")
        filepath = self.base_path / "grants" / f"{grant_id}.json"
        filepath.write_text(self._serialize(grant), encoding="utf-8")
        logger.info(f"Saved grant: {grant_id}")
        return grant_id

    def _get_drafted_grant_ids(self) -> set[str]:
        """Get set of all grant_ids that have an existing draft."""
        drafted = set()
        apps_dir = self.base_path / "applications"
        for filepath in apps_dir.glob("*.json"):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                gid = data.get("grant_id")
                if gid:
                    drafted.add(str(gid))
            except Exception:
                pass
        return drafted

    def _normalize_grant(self, grant: dict, drafted_set: Optional[set[str]] = None) -> dict:
        """Ensure match_score has total computed and attach is_drafted boolean."""
        ms = grant.get("match_score")
        if isinstance(ms, dict):
            if "total" not in ms:
                ms["total"] = (
                    ms.get("mission_alignment", 0)
                    + ms.get("eligibility_fit", 0)
                    + ms.get("capacity_match", 0)
                    + ms.get("geographic_fit", 0)
                    + ms.get("track_record", 0)
                )
        gid = str(grant.get("grant_id") or grant.get("id") or "")
        if drafted_set is not None:
            grant["is_drafted"] = gid in drafted_set
        else:
            grant["is_drafted"] = gid in self._get_drafted_grant_ids()
        return grant

    def get_grant(self, grant_id: str) -> Optional[dict]:
        """Retrieve a grant opportunity."""
        filepath = self.base_path / "grants" / f"{grant_id}.json"
        if filepath.exists():
            grant = json.loads(filepath.read_text(encoding="utf-8"))
            return self._normalize_grant(grant)
        return None

    def list_grants(self, status: str = "") -> list[dict]:
        """List all grants, optionally filtered by status."""
        grants = []
        grants_dir = self.base_path / "grants"
        drafted_set = self._get_drafted_grant_ids()
        for filepath in grants_dir.glob("*.json"):
            try:
                grant = json.loads(filepath.read_text(encoding="utf-8"))
                if not status or grant.get("status") == status:
                    grants.append(self._normalize_grant(grant, drafted_set=drafted_set))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to read grant file {filepath}: {e}")
        return sorted(grants, key=lambda g: g.get("discovered_at", ""), reverse=True)

    def grant_exists(self, grant_id: str) -> bool:
        """Check if a grant already exists in storage."""
        filepath = self.base_path / "grants" / f"{grant_id}.json"
        return filepath.exists()

    # ── Application Operations ──

    def save_application(self, application: dict) -> str:
        """Save an application draft."""
        draft_id = application.get("draft_id", "unknown")
        filepath = self.base_path / "applications" / f"{draft_id}.json"
        filepath.write_text(self._serialize(application), encoding="utf-8")
        logger.info(f"Saved application draft: {draft_id}")
        return draft_id

    def get_application(self, draft_id: str) -> Optional[dict]:
        """Retrieve an application draft."""
        filepath = self.base_path / "applications" / f"{draft_id}.json"
        if filepath.exists():
            return json.loads(filepath.read_text(encoding="utf-8"))
        return None

    def list_applications(self) -> list[dict]:
        """List all application drafts."""
        apps = []
        apps_dir = self.base_path / "applications"
        for filepath in apps_dir.glob("*.json"):
            try:
                app = json.loads(filepath.read_text(encoding="utf-8"))
                apps.append(app)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to read application file {filepath}: {e}")
        return sorted(apps, key=lambda a: a.get("created_at", ""), reverse=True)

    # ── Activity Operations ──

    def add_activity(self, event: dict) -> None:
        """Add an activity event to the feed."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        filepath = self.base_path / "activity" / f"{timestamp}.json"
        filepath.write_text(self._serialize(event), encoding="utf-8")

    def get_recent_activity(self, limit: int = 20) -> list[dict]:
        """Get the most recent activity events."""
        events = []
        activity_dir = self.base_path / "activity"
        files = sorted(activity_dir.glob("*.json"), reverse=True)
        for filepath in files[:limit]:
            try:
                event = json.loads(filepath.read_text(encoding="utf-8"))
                events.append(event)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to read activity file {filepath}: {e}")
        return events

    # ── Stats ──

    def get_stats(self) -> dict:
        """Calculate dashboard statistics from stored data."""
        grants = self.list_grants()
        apps = self.list_applications()

        high_matches = [
            g for g in grants
            if g.get("match_score") and g["match_score"].get("mission_alignment", 0)
            + g["match_score"].get("eligibility_fit", 0)
            + g["match_score"].get("capacity_match", 0)
            + g["match_score"].get("geographic_fit", 0)
            + g["match_score"].get("track_record", 0) >= 70
        ]

        # Find the nearest deadline
        next_deadline = None
        days_until = None
        now_dt = datetime.now(timezone.utc)
        for g in grants:
            close = g.get("close_date")
            if close and g.get("status") not in ("archived", "submitted"):
                try:
                    # Handle various date formats
                    for fmt in ["%Y-%m-%d", "%b %d, %Y", "%m/%d/%Y"]:
                        try:
                            close_dt = datetime.strptime(close.split(" ")[0], fmt).replace(tzinfo=timezone.utc)
                            delta = (close_dt - now_dt).days
                            if delta > 0 and (days_until is None or delta < days_until):
                                days_until = delta
                                next_deadline = close
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass

        active_grant_ids = {g.get("grant_id") for g in grants if g.get("grant_id")}
        unique_drafted = {
            app.get("grant_id")
            for app in apps
            if app.get("grant_id") in active_grant_ids
        }

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Determine last scan timestamp from activity or discovered grants
        last_scan = None
        activity = self.get_recent_activity(limit=20)
        for ev in activity:
            ev_type = str(ev.get("event_type") or ev.get("type") or "").lower()
            ev_msg = str(ev.get("message") or "").lower()
            if "scan" in ev_type or "scan" in ev_msg:
                ts = ev.get("timestamp")
                if ts:
                    try:
                        last_scan = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                        break
                    except Exception:
                        pass
        if not last_scan and grants:
            dates = [g.get("discovered_at") for g in grants if g.get("discovered_at")]
            if dates:
                latest_d = max(dates)
                if isinstance(latest_d, datetime):
                    last_scan = latest_d
                elif isinstance(latest_d, str):
                    try:
                        last_scan = datetime.fromisoformat(latest_d.replace("Z", "+00:00"))
                    except Exception:
                        pass
        if not last_scan:
            last_scan = datetime.now(timezone.utc)

        return {
            "grants_discovered": len(grants),
            "grants_this_week": len([
                g for g in grants
                if g.get("discovered_at", "")[:10] >= today_str
            ]),
            "high_matches": len(high_matches),
            "applications_drafted": len(unique_drafted),
            "next_deadline": next_deadline,
            "days_until_deadline": days_until,
            "last_scan": last_scan,
        }


# Global storage instance
storage = LocalStorage()
