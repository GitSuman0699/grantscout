"""GrantScout API Server.

FastAPI application serving the GrantScout dashboard and
providing endpoints for the agent pipeline.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone

# Force stdout and stderr to UTF-8 to prevent charmap encoding errors during agent streaming on Windows
if sys.stdout.encoding != "utf-8" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8" and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

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
event_queues: list[asyncio.Queue] = []

async def broadcast_event(event: dict):
    for q in event_queues:
        await q.put(event)


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
async def dashboard_stream(request: Request):
    """Server-Sent Events stream for real-time dashboard updates."""
    q = asyncio.Queue()
    event_queues.append(q)

    async def event_generator() -> AsyncGenerator:
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=20.0)
                    yield {"event": event.get("type", "update"), "data": json.dumps(event)}
                except asyncio.TimeoutError:
                    yield {"event": "heartbeat", "data": json.dumps({"type": "heartbeat"})}
        finally:
            if q in event_queues:
                event_queues.remove(q)

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
    profile.updated_at = datetime.now(timezone.utc)

    storage.save_org_profile(profile.model_dump())

    # Log activity
    storage.add_activity({
        "event_type": "profile_updated",
        "message": f"Organization profile updated: {profile.name} (by {auth.sub})",
        "timestamp": datetime.now(timezone.utc).isoformat(),
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


from backend.rag.knowledge_base import knowledge_base

# ──────────────────────────────────────────────
#  RAG Knowledge Base Endpoints
# ──────────────────────────────────────────────


@app.get("/api/documents")
async def list_knowledge_base_documents():
    """List all organizational documents indexed in the RAG Knowledge Base."""
    docs = knowledge_base.list_documents()
    return {"documents": docs, "total": len(docs)}


@app.post("/api/documents/search")
async def search_knowledge_base(payload: dict):
    """Semantic vector search against indexed nonprofit documents."""
    query = payload.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="Query string is required")
    top_k = int(payload.get("top_k", 3))
    category = payload.get("category")
    results = knowledge_base.search(query=query, top_k=top_k, category=category)
    return {"query": query, "count": len(results), "results": [r.model_dump() for r in results]}


@app.post("/api/documents/index")
async def index_document(
    payload: dict,
    auth: TokenPayload = Depends(get_current_auth),
):
    """Index a new document into the RAG Knowledge Base (Authenticated)."""
    doc_name = payload.get("doc_name", "")
    content = payload.get("content", "")
    category = payload.get("category", "general")

    if not doc_name or not content:
        raise HTTPException(status_code=400, detail="doc_name and content are required")

    chunks_indexed = knowledge_base.add_document(doc_name, content, category)
    return {"status": "indexed", "doc_name": doc_name, "chunks": chunks_indexed, "indexed_by": auth.sub}


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
        
    app_draft["updated_at"] = datetime.now(timezone.utc).isoformat()
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

        import asyncio
        loop = asyncio.get_running_loop()
        def on_agent_thought(msg: str):
            asyncio.run_coroutine_threadsafe(
                broadcast_event({
                    "type": "agent_thought",
                    "message": msg,
                    "grant_id": grant_id
                }),
                loop
            )

        await broadcast_event({
            "type": "drafting_started",
            "message": f"INITIALIZING DRAFTER SWARM...",
            "grant_id": grant_id,
        })

        result = await asyncio.to_thread(draft_application_for_grant, grant, on_agent_thought)

        # Check drafted application
        apps = storage.list_applications()
        matched_app = next((a for a in apps if a.get("grant_id") == grant_id), None)

        await broadcast_event({
            "type": "application_drafted",
            "message": f"Draft proposal ready for '{grant.get('title')}'",
            "grant_id": grant_id,
            "draft_id": matched_app.get("draft_id") if matched_app else None,
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
        from backend.agents.orchestrator import run_orchestrator

        storage.add_activity({
            "event_type": "scan_started",
            "message": f"Grant scan initiated across federal databases (by {auth.sub})...",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        await broadcast_event({
            "type": "scan_started",
            "message": "Grant scan initiated...",
        })

        result = await run_orchestrator()

        storage.add_activity({
            "event_type": "scan_completed",
            "message": "Grant scan completed successfully",
            "details": {"result_preview": result[:200] if result else ""},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        await broadcast_event({
            "type": "scan_completed",
            "message": "Grant scan completed!",
        })

        return {"status": "completed", "result": result, "triggered_by": auth.sub}

    except Exception as e:
        logger.error(f"Scan failed: {e}")
        storage.add_activity({
            "event_type": "error",
            "message": f"Grant scan failed: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        summary = run_full_orchestration_cycle()

        await broadcast_event({
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
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ──────────────────────────────────────────────
#  Multi-Tenant Personas & Onboarding Endpoints
# ──────────────────────────────────────────────

from backend.storage.personas import PERSONAS, get_persona_by_id, persona_to_org_profile
from backend.tools.compliance import audit_application_compliance
from pydantic import BaseModel


class PersonaSwitchRequest(BaseModel):
    persona_id: str


@app.get("/api/personas")
async def list_nonprofit_personas():
    """List available multi-tenant nonprofit personas."""
    return {"personas": [p.model_dump() for p in PERSONAS]}


@app.post("/api/personas/switch")
async def switch_nonprofit_persona(
    payload: PersonaSwitchRequest,
    auth: TokenPayload = Depends(get_current_auth),
):
    """Switch active nonprofit persona and update discovery keywords."""
    persona = get_persona_by_id(payload.persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail=f"Persona '{payload.persona_id}' not found.")

    profile = persona_to_org_profile(persona)
    storage.save_org_profile(profile.model_dump())

    event = {
        "event_id": f"evt-{uuid.uuid4().hex[:8]}",
        "event_type": "profile_updated",
        "message": f"Switched active sector persona to '{persona.name}' ({persona.sector})",
        "details": {"persona_id": persona.id, "keywords": persona.keywords},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    storage.add_activity(event)
    await broadcast_event(event)

    logger.info(f"Switched active persona to {persona.name}")
    return {"status": "success", "active_persona": persona.model_dump()}


@app.post("/api/org/onboard")
async def onboard_nonprofit_organization(
    profile: OrgProfile,
    auth: TokenPayload = Depends(get_current_auth),
):
    """Onboard a custom nonprofit organization with Form 990 / mission extraction."""
    profile.org_id = "default"
    profile.name = sanitize_input(profile.name, "name")
    profile.mission = sanitize_input(profile.mission, "mission")
    profile.service_area = sanitize_input(profile.service_area, "service_area")
    profile.target_population = sanitize_input(profile.target_population, "target_population")

    storage.save_org_profile(profile.model_dump())

    event = {
        "event_id": f"evt-{uuid.uuid4().hex[:8]}",
        "event_type": "profile_updated",
        "message": f"Onboarded organization profile for '{profile.name}'",
        "details": {"ein": profile.ein, "budget": profile.annual_budget},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    storage.add_activity(event)
    await broadcast_event(event)

    return {"status": "success", "profile": profile.model_dump()}


# ──────────────────────────────────────────────
#  2 CFR 200 Compliance Audit Endpoints
# ──────────────────────────────────────────────


class ComplianceAuditRequest(BaseModel):
    draft_id: str = ""
    budget_narrative: str = ""
    project_design: str = ""


@app.post("/api/grants/{grant_id}/compliance-audit")
async def audit_grant_compliance(
    grant_id: str,
    payload: ComplianceAuditRequest = None,
    auth: TokenPayload = Depends(get_current_auth),
):
    """Run an automated 2 CFR 200 Uniform Guidance regulatory compliance audit."""
    req_payload = payload or ComplianceAuditRequest()
    audit_result = audit_application_compliance(
        grant_id=grant_id,
        draft_id=req_payload.draft_id,
        budget_narrative=req_payload.budget_narrative,
        project_design=req_payload.project_design,
    )
    return audit_result


# ──────────────────────────────────────────────
#  Cost & Token Optimization Endpoints
# ──────────────────────────────────────────────

from backend.optimization import (
    response_cache,
    token_tracker,
    get_model_for_agent,
    MODEL_TIERS,
    AGENT_TIER_MAP,
)


@app.get("/api/optimization/token-usage")
async def get_token_usage():
    """Get per-agent token usage, estimated costs, and cache savings."""
    return token_tracker.summary


@app.get("/api/optimization/cache-stats")
async def get_cache_stats():
    """Get response cache performance metrics (hits, misses, hit rate)."""
    return response_cache.stats


@app.get("/api/optimization/model-tiers")
async def get_model_tiers():
    """Get the tiered model routing configuration for all agents."""
    tiers = {}
    for tier_name, model_cfg in MODEL_TIERS.items():
        tiers[tier_name.value] = {
            "model_id": model_cfg.model_id,
            "region": model_cfg.region,
            "cost_per_1k_input": model_cfg.cost_per_1k_input,
            "cost_per_1k_output": model_cfg.cost_per_1k_output,
            "max_tokens": model_cfg.max_tokens,
            "description": model_cfg.description,
        }
    agent_map = {agent: tier.value for agent, tier in AGENT_TIER_MAP.items()}
    return {"tiers": tiers, "agent_routing": agent_map}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,
    )

