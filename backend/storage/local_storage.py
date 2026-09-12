"""Local file-based storage for development without AWS.

Provides the same interface as S3/DynamoDB but stores data
as JSON files on the local filesystem. This allows full
development and testing without AWS credentials.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import config

logger = logging.getLogger(__name__)


class LocalStorage:
    """File-based storage backend for local development."""

    def __init__(self, base_path: str = ""):
        self.base_path = Path(base_path or config.LOCAL_STORAGE_PATH)
        self._write_lock = threading.Lock()
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

    def _atomic_write(self, filepath: Path, data: str) -> None:
        """Write data to file atomically using temp-file-then-rename.

        This prevents file corruption from concurrent writes by ensuring
        the target file is either the old complete version or the new
        complete version — never a partial write.
        """
        with self._write_lock:
            dir_path = filepath.parent
            tmp_path = None
            try:
                fd, tmp_path = tempfile.mkstemp(dir=str(dir_path), suffix=".tmp")
                with os.fdopen(fd, "w", encoding="utf-8") as tmp_f:
                    tmp_f.write(data)
                    tmp_f.flush()
                    os.fsync(tmp_f.fileno())
                # Atomic rename (on POSIX) / replace (on Windows)
                os.replace(tmp_path, str(filepath))
            except Exception:
                # Clean up temp file on failure
                if tmp_path is not None:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
                raise

    # ── Org Profile Operations ──

    def save_org_profile(self, profile: dict) -> str:
        """Save an organization profile."""
        org_id = profile.get("org_id", "default")
        filepath = self.base_path / "org_profiles" / f"{org_id}.json"
        self._atomic_write(filepath, self._serialize(profile))
        logger.info(f"Saved org profile: {org_id}")
        return org_id

    def get_org_profile(self, org_id: str = "default") -> dict | None:
        """Retrieve an organization profile."""
        filepath = self.base_path / "org_profiles" / f"{org_id}.json"
        if filepath.exists():
            return json.loads(filepath.read_text(encoding="utf-8"))
        return None

    # ── Grant Operations ──

    def _get_grant_dedup_keys(self, grant: dict) -> list[str]:
        """Extract all valid identity signals: numeric ID, solicitation codes, and title slug."""
        keys = set()
        opp_id = str(grant.get("id") or "").strip()
        if opp_id.isdigit() and len(opp_id) >= 5:
            keys.add(f"id:{opp_id}")

        raw_gid = str(grant.get("grant_id") or "").strip()
        clean_num = raw_gid.replace("grants-gov-", "").strip()
        if clean_num.isdigit() and len(clean_num) >= 5:
            keys.add(f"id:{clean_num}")

        for url_field in (grant.get("application_url"), grant.get("url"), grant.get("additional_info_url")):
            if url_field and isinstance(url_field, str):
                m = re.search(r"(?:oppId=|opp_id=|detail/)(\d{5,8})", url_field, re.IGNORECASE)
                if m:
                    keys.add(f"id:{m.group(1)}")

        opp_num = str(grant.get("opportunity_number") or "").strip().upper()
        raw_codes = f"{opp_num} {raw_gid}"
        for m in re.finditer(r"([A-Z]{2,5}-\d{2,3}-\d{2,4}|\d{2,3}-\d{3,5})", raw_codes):
            keys.add(f"opp:{m.group(1).upper()}")
        if opp_num and len(opp_num) >= 4:
            keys.add(f"opp:{opp_num}")

        title = str(grant.get("title") or "").strip().lower()
        slug = re.sub(r"[^a-z0-9]", "", title)[:28]
        if slug and len(slug) >= 10:
            keys.add(f"title:{slug}")

        return list(keys)

    def _get_grant_dedup_key(self, grant: dict) -> str:
        """Derive a primary canonical deduplication key dynamically."""
        keys = self._get_grant_dedup_keys(grant)
        for prefix in ("id:", "opp:", "title:"):
            for k in keys:
                if k.startswith(prefix):
                    return k
        return f"raw:{grant.get('grant_id') or grant.get('id') or 'unknown'}"

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

    def _normalize_grant(self, grant: dict, drafted_set: set[str] | None = None) -> dict:
        """Ensure canonical IDs, Grants.gov details URL, and compute match totals."""
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

        # Resolve canonical Grants.gov ID
        keys = self._get_grant_dedup_keys(grant)
        opp_id = ""
        for k in keys:
            if k.startswith("id:"):
                opp_id = k.replace("id:", "")
                break

        if opp_id:
            grant["id"] = opp_id
            grant["grant_id"] = f"grants-gov-{opp_id}"
            grant["application_url"] = f"https://www.grants.gov/search-results-detail/{opp_id}"
            grant["url"] = grant["application_url"]
        else:
            raw_gid = str(grant.get("grant_id") or grant.get("id") or "").strip()
            opp_num = str(grant.get("opportunity_number") or raw_gid).strip()
            current_url = str(grant.get("application_url") or grant.get("url") or "")
            if not current_url.startswith("https://www.grants.gov"):
                grant["application_url"] = f"https://www.grants.gov/search-grants?keywords={opp_num}"
                grant["url"] = grant["application_url"]

        gid = str(grant.get("grant_id") or "")
        if drafted_set is not None:
            grant["is_drafted"] = gid in drafted_set
        else:
            grant["is_drafted"] = gid in self._get_drafted_grant_ids()

        return grant

    def save_grant(self, grant: dict) -> str:
        """Save a grant opportunity with automatic multi-key deduplication and Grants.gov URL enforcement."""
        self._normalize_grant(grant)
        keys = set(self._get_grant_dedup_keys(grant))

        canonical_gid = grant.get("grant_id", "unknown")
        filepath = self.base_path / "grants" / f"{canonical_gid}.json"

        # Check existing files for duplicate matches and merge/clean up
        grants_dir = self.base_path / "grants"
        for existing_file in grants_dir.glob("*.json"):
            if existing_file == filepath:
                continue
            try:
                existing_data = json.loads(existing_file.read_text(encoding="utf-8"))
                existing_keys = set(self._get_grant_dedup_keys(existing_data))
                if keys.intersection(existing_keys):
                    logger.info(f"Deduplicating: Merging {existing_file.name} into {filepath.name}")
                    if existing_data.get("is_drafted"):
                        grant["is_drafted"] = True
                    if existing_data.get("status") in ("ready_for_review", "drafting") and grant.get("status") == "matched":
                        grant["status"] = existing_data.get("status")
                    try:
                        existing_file.unlink()
                    except Exception:
                        pass
            except Exception:
                pass

        self._atomic_write(filepath, self._serialize(grant))
        logger.info(f"Saved grant: {canonical_gid}")
        return canonical_gid

    def get_grant(self, grant_id: str) -> dict | None:
        """Retrieve a grant opportunity."""
        filepath = self.base_path / "grants" / f"{grant_id}.json"
        if filepath.exists():
            grant = json.loads(filepath.read_text(encoding="utf-8"))
            return self._normalize_grant(grant)

        # Try searching by multi-key match
        search_keys = set(self._get_grant_dedup_keys({"grant_id": grant_id, "id": grant_id, "opportunity_number": grant_id}))
        grants_dir = self.base_path / "grants"
        for f in grants_dir.glob("*.json"):
            try:
                g = json.loads(f.read_text(encoding="utf-8"))
                g_keys = set(self._get_grant_dedup_keys(g))
                if search_keys.intersection(g_keys):
                    return self._normalize_grant(g)
            except Exception:
                pass
        return None

    def list_grants(self, status: str = "") -> list[dict]:
        """List all grants, deduplicated dynamically so each federal opportunity appears exactly once."""
        canonical_groups: list[dict] = []  # List of {"keys": set, "grant": dict, "filepath": Path}
        grants_dir = self.base_path / "grants"
        drafted_set = self._get_drafted_grant_ids()
        files_to_clean: list[Path] = []

        for filepath in sorted(grants_dir.glob("*.json")):
            try:
                grant = json.loads(filepath.read_text(encoding="utf-8"))
                norm_grant = self._normalize_grant(grant, drafted_set=drafted_set)
                item_keys = set(self._get_grant_dedup_keys(norm_grant))

                matched = None
                for grp in canonical_groups:
                    if item_keys.intersection(grp["keys"]):
                        matched = grp
                        break

                if not matched:
                    canonical_groups.append({
                        "keys": item_keys,
                        "grant": norm_grant,
                        "filepath": filepath,
                    })
                else:
                    matched["keys"].update(item_keys)
                    existing = matched["grant"]
                    # Merge attributes
                    if norm_grant.get("is_drafted"):
                        existing["is_drafted"] = True
                    if norm_grant.get("status") in ("ready_for_review", "drafting"):
                        existing["status"] = norm_grant["status"]
                    if str(norm_grant.get("grant_id", "")).startswith("grants-gov-") and not str(existing.get("grant_id", "")).startswith("grants-gov-"):
                        matched["grant"] = norm_grant
                    files_to_clean.append(filepath)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to read grant file {filepath}: {e}")

        # Clean duplicate files from disk
        for f in files_to_clean:
            try:
                f.unlink()
            except Exception:
                pass

        all_grants = [grp["grant"] for grp in canonical_groups]
        if status:
            all_grants = [g for g in all_grants if g.get("status") == status]

        return sorted(all_grants, key=lambda g: g.get("discovered_at", ""), reverse=True)

    def grant_exists(self, grant_id: str) -> bool:
        """Check if a grant already exists in storage, checking all IDs and titles."""
        filepath = self.base_path / "grants" / f"{grant_id}.json"
        if filepath.exists():
            return True

        search_keys = set(self._get_grant_dedup_keys({"grant_id": grant_id, "id": grant_id, "opportunity_number": grant_id}))
        grants_dir = self.base_path / "grants"
        for f in grants_dir.glob("*.json"):
            try:
                g = json.loads(f.read_text(encoding="utf-8"))
                g_keys = set(self._get_grant_dedup_keys(g))
                if search_keys.intersection(g_keys):
                    return True
            except Exception:
                pass
        return False

    def delete_grant(self, grant_id: str) -> bool:
        """Delete a grant opportunity."""
        filepath = self.base_path / "grants" / f"{grant_id}.json"
        if filepath.exists():
            filepath.unlink()
            logger.info(f"Deleted grant: {grant_id}")
            return True
        return False

    def clear_all_grants(self) -> int:
        """Clear all stored grants."""
        grants_dir = self.base_path / "grants"
        count = 0
        for filepath in grants_dir.glob("*.json"):
            try:
                filepath.unlink()
                count += 1
            except Exception as e:
                logger.warning(f"Failed to delete {filepath}: {e}")
        return count



    # ── Application Operations ──

    def save_application(self, application: dict) -> str:
        """Save an application draft atomically.

        Uses temp-file-then-rename under a threading lock to prevent
        corruption when multiple swarm agents write concurrently.
        """
        draft_id = application.get("draft_id", "unknown")
        filepath = self.base_path / "applications" / f"{draft_id}.json"
        self._atomic_write(filepath, self._serialize(application))
        logger.info(f"Saved application draft: {draft_id}")
        return draft_id

    def find_application_by_grant_id(self, grant_id: str) -> dict | None:
        """Find an application draft by grant_id (instead of draft_id).

        This avoids scanning all files when we know the grant_id but
        not the draft_id.
        """
        apps_dir = self.base_path / "applications"
        for filepath in apps_dir.glob("*.json"):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                if data.get("grant_id") == grant_id:
                    return data
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Skipping corrupted application file {filepath.name}: {e}")
        return None

    def get_application(self, draft_id: str) -> dict | None:
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

    def delete_application(self, draft_id: str) -> bool:
        """Delete an application draft."""
        filepath = self.base_path / "applications" / f"{draft_id}.json"
        if filepath.exists():
            filepath.unlink()
            logger.info(f"Deleted application draft: {draft_id}")
            return True
        return False

    def clear_all_applications(self) -> int:
        """Clear all stored applications."""
        apps_dir = self.base_path / "applications"
        count = 0
        for filepath in apps_dir.glob("*.json"):
            try:
                filepath.unlink()
                count += 1
            except Exception as e:
                logger.warning(f"Failed to delete {filepath}: {e}")
        return count


    # ── Activity Operations ──

    def add_activity(self, event: dict) -> None:
        """Add an activity event to the feed."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        filepath = self.base_path / "activity" / f"{timestamp}.json"
        self._atomic_write(filepath, self._serialize(event))

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

    def clear_all_activity(self) -> int:
        """Clear all stored activity events."""
        activity_dir = self.base_path / "activity"
        count = 0
        for filepath in activity_dir.glob("*.json"):
            try:
                filepath.unlink()
                count += 1
            except Exception as e:
                logger.warning(f"Failed to delete {filepath}: {e}")
        return count

    def purge_all_data(self) -> dict[str, int]:
        """Purge all grants, applications, and activity records."""
        grants_cleared = self.clear_all_grants()
        apps_cleared = self.clear_all_applications()
        activity_cleared = self.clear_all_activity()
        logger.info(
            f"Purged storage: {grants_cleared} grants, {apps_cleared} applications, {activity_cleared} activities"
        )
        return {
            "grants_cleared": grants_cleared,
            "applications_cleared": apps_cleared,
            "activity_cleared": activity_cleared,
        }

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
