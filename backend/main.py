"""GrantScout API Server.

FastAPI application serving the GrantScout dashboard and
providing endpoints for the agent pipeline.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from backend.api.models.schemas import (
    OrgProfile,
    GrantOpportunity,
    DashboardStats,
    ActivityEvent,
)
from backend.config import config
from backend.storage.local_storage import storage
from backend.security.auth import get_current_auth, TokenPayload, sanitize_input
from backend.api.routes.auth import router as auth_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("grantscout")

# Global event queue for SSE notifications
event_queue: asyncio.Queue = asyncio.Queue()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle handler."""
    logger.info("🚀 GrantScout API starting up...")
    logger.info(f"   Storage: Local ({config.LOCAL_STORAGE_PATH})")
    logger.info(f"   Model: {config.BEDROCK_MODEL_ID}")
    logger.info(f"   Security: {'Enabled (JWT + API Key)' if config.AUTH_ENABLED else 'Disabled (Dev Mode)'}")
    yield
    logger.info("GrantScout API shutting down...")


app = FastAPI(
    title="GrantScout API",
    description="AI-powered autonomous grant discovery for small nonprofits",
    version="1.0.0",
    lifespan=lifespan,
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Inject hardened HTTP security headers into all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Auth Router
app.include_router(auth_router)


# ──────────────────────────────────────────────
#  Dashboard Endpoints
# ──────────────────────────────────────────────


@app.get("/api/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get summary statistics for the dashboard."""
    stats = storage.get_stats()
    return DashboardStats(**stats)


@app.get("/api/dashboard/activity")
async def get_recent_activity():
    """Get recent agent activity events."""
    events = storage.get_recent_activity(limit=20)
    return {"events": events}


@app.get("/api/dashboard/stream")
async def dashboard_stream():
    """Server-Sent Events stream for real-time dashboard updates."""

    async def event_generator() -> AsyncGenerator:
        while True:
            try:
                # Wait for an event with timeout (sends heartbeat if no events)
                event = await asyncio.wait_for(event_queue.get(), timeout=30.0)
                yield {"event": event.get("type", "update"), "data": str(event)}
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                yield {"event": "heartbeat", "data": "ping"}

    return EventSourceResponse(event_generator())


# ──────────────────────────────────────────────
#  Organization Profile Endpoints
# ──────────────────────────────────────────────


@app.post("/api/org/profile")
async def create_or_update_org_profile(
    profile: OrgProfile,
    auth: TokenPayload = Depends(get_current_auth),
):
    """Create or update the organization profile (Authenticated)."""
    if not profile.org_id:
        profile.org_id = auth.org_id or "default"
    
    # Sanitize text fields
    profile.name = sanitize_input(profile.name, "org_name")
    profile.mission = sanitize_input(profile.mission, "mission")
    profile.service_area = sanitize_input(profile.service_area, "service_area")
    profile.target_population = sanitize_input(profile.target_population, "target_population")
    profile.updated_at = datetime.utcnow()

    storage.save_org_profile(profile.model_dump())

    # Log activity
    storage.add_activity({
        "event_type": "profile_updated",
        "message": f"Organization profile updated: {profile.name} (by {auth.sub})",
        "timestamp": datetime.utcnow().isoformat(),
    })

    return {"status": "saved", "org_id": profile.org_id, "updated_by": auth.sub}


@app.get("/api/org/profile")
async def get_org_profile():
    """Get the current organization profile."""
    profile = storage.get_org_profile("default")
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="No organization profile found. Please set up your profile first.",
        )
    return profile


# ──────────────────────────────────────────────
#  Grant Endpoints
# ──────────────────────────────────────────────


@app.get("/api/grants")
async def list_grants(status: str = ""):
    """List all discovered grants, optionally filtered by status."""
    grants = storage.list_grants(status=status)
    return {"grants": grants, "total": len(grants)}


@app.get("/api/grants/{grant_id}")
async def get_grant(grant_id: str):
    """Get details of a specific grant."""
    grant = storage.get_grant(grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")
    return grant


# ──────────────────────────────────────────────
#  Application Endpoints
# ──────────────────────────────────────────────


@app.get("/api/applications")
async def list_applications():
    """List all application drafts."""
    apps = storage.list_applications()
    return {"applications": apps, "total": len(apps)}


@app.get("/api/applications/{draft_id}")
async def get_application(draft_id: str):
    """Get a specific application draft."""
    app_draft = storage.get_application(draft_id)
    if not app_draft:
        raise HTTPException(status_code=404, detail="Application draft not found")
    return app_draft


@app.put("/api/applications/{draft_id}")
async def update_application(
    draft_id: str,
    payload: dict,
    auth: TokenPayload = Depends(get_current_auth),
):
    """Update sections or content of an application draft (Authenticated)."""
    app_draft = storage.get_application(draft_id)
    if not app_draft:
        raise HTTPException(status_code=404, detail="Application draft not found")

    if "sections" in payload:
        # Sanitize section contents
        for s in payload["sections"]:
            if "content" in s:
                s["content"] = sanitize_input(s["content"], s.get("title", "section"))
        app_draft["sections"] = payload["sections"]

    if "grant_title" in payload:
        app_draft["grant_title"] = sanitize_input(payload["grant_title"], "grant_title")
        
    app_draft["updated_at"] = datetime.utcnow().isoformat()
    storage.save_application(app_draft)
    return {"status": "updated", "draft": app_draft, "updated_by": auth.sub}


@app.post("/api/grants/{grant_id}/draft")
async def trigger_grant_draft(
    grant_id: str,
    auth: TokenPayload = Depends(get_current_auth),
):
    """Trigger the Drafter Agent to pre-fill a grant application (Authenticated)."""
    grant = storage.get_grant(grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")

    try:
        from backend.agents.drafter import draft_application_for_grant

        # Update status
        grant["status"] = "drafting"
        storage.save_grant(grant)

        await event_queue.put({
            "type": "drafting_started",
            "message": f"Drafting application for '{grant.get('title')}'...",
        })

        result = draft_application_for_grant(grant)
        
        # Check drafted application
        apps = storage.list_applications()
        matched_app = next((a for a in apps if a.get("grant_id") == grant_id), None)

        await event_queue.put({
            "type": "application_drafted",
            "message": f"Draft ready for '{grant.get('title')}'",
        })

        return {"status": "drafted", "result": result, "application": matched_app, "requested_by": auth.sub}

    except Exception as e:
        logger.error(f"Drafting failed: {e}")
        grant["status"] = "matched"
        storage.save_grant(grant)
        raise HTTPException(status_code=500, detail=f"Drafting failed: {str(e)}")


# ──────────────────────────────────────────────
#  Agent Control Endpoints
# ──────────────────────────────────────────────


@app.post("/api/agent/scan")
async def trigger_scan(auth: TokenPayload = Depends(get_current_auth)):
    """Manually trigger a grant scan (Authenticated)."""
    try:
        from backend.agents.scanner import run_scan

        storage.add_activity({
            "event_type": "scan_started",
            "message": f"Grant scan initiated across federal databases (by {auth.sub})...",
            "timestamp": datetime.utcnow().isoformat(),
        })

        await event_queue.put({
            "type": "scan_started",
            "message": "Grant scan initiated...",
        })

        result = await run_scan()

        storage.add_activity({
            "event_type": "scan_completed",
            "message": "Grant scan completed successfully",
            "details": {"result_preview": result[:200] if result else ""},
            "timestamp": datetime.utcnow().isoformat(),
        })

        await event_queue.put({
            "type": "scan_completed",
            "message": "Grant scan completed!",
        })

        return {"status": "completed", "result": result, "triggered_by": auth.sub}

    except Exception as e:
        logger.error(f"Scan failed: {e}")
        storage.add_activity({
            "event_type": "error",
            "message": f"Grant scan failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
        })
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@app.post("/api/agent/orchestrate")
async def trigger_full_orchestration(auth: TokenPayload = Depends(get_current_auth)):
    """Trigger the complete autonomous Orchestrator cycle (Authenticated)."""
    try:
        from backend.agents.orchestrator import run_full_orchestration_cycle

        storage.add_activity({
            "event_type": "scan_started",
            "message": f"Full autonomous orchestration cycle running in background (triggered by {auth.sub})...",
            "timestamp": datetime.utcnow().isoformat(),
        })

        summary = run_full_orchestration_cycle()

        await event_queue.put({
            "type": "orchestration_completed",
            "message": f"Autonomous cycle finished: {summary.get('grants_scanned', 0)} opportunities processed",
        })

        return {"status": "completed", "summary": summary, "triggered_by": auth.sub}

    except Exception as e:
        logger.error(f"Orchestration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Orchestration failed: {str(e)}")


@app.post("/api/agent/deadlines")
async def trigger_deadline_check(auth: TokenPayload = Depends(get_current_auth)):
    """Trigger a deadline monitoring sweep across active opportunities (Authenticated)."""
    try:
        from backend.agents.deadline import run_deadline_check

        summary = run_deadline_check()
        return {"status": "completed", "summary": summary, "triggered_by": auth.sub}

    except Exception as e:
        logger.error(f"Deadline sweep failed: {e}")
        raise HTTPException(status_code=500, detail=f"Deadline sweep failed: {str(e)}")


@app.post("/api/agent/score/{grant_id}")
async def trigger_scoring(
    grant_id: str,
    auth: TokenPayload = Depends(get_current_auth),
):
    """Manually trigger scoring for a specific grant (Authenticated)."""
    try:
        grant = storage.get_grant(grant_id)
        if not grant:
            raise HTTPException(status_code=404, detail="Grant not found")

        from backend.agents.matcher import score_grant

        result = score_grant(grant)
        return {"status": "scored", "result": result, "triggered_by": auth.sub}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scoring failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")


@app.get("/api/agent/status")
async def get_agent_status():
    """Get the current agent status."""
    activity = storage.get_recent_activity(limit=1)
    last_scan = None
    if activity:
        last_scan = activity[0].get("timestamp")

    return {
        "status": "active",
        "last_activity": last_scan,
        "scan_interval_hours": config.SCAN_INTERVAL_HOURS,
    }


# ──────────────────────────────────────────────
#  Health Check
# ──────────────────────────────────────────────


@app.get("/health")
async def health_check():
    """API health check endpoint."""
    return {
        "status": "healthy",
        "service": "grantscout-api",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,
    )
