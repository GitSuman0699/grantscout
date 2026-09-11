"""GrantScout API Server.

FastAPI application serving the GrantScout dashboard and
providing endpoints for the agent pipeline.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

# Force stdout and stderr to UTF-8 to prevent charmap encoding errors during agent streaming on Windows
_reconfig_out = getattr(sys.stdout, "reconfigure", None)
if _reconfig_out:
    _reconfig_out(encoding="utf-8")
_reconfig_err = getattr(sys.stderr, "reconfigure", None)
if _reconfig_err:
    _reconfig_err(encoding="utf-8")

from collections.abc import AsyncGenerator
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from backend.api.models.schemas import (
    DashboardStats,
    OrgProfile,
)
from backend.config import config
from backend.security.auth import TokenPayload, get_current_auth, sanitize_input
from backend.storage.local_storage import storage

# ==========================================
# REMOTE AGENT INVOCATIONS (DECOUPLED)
# These stub functions replace the deleted backend/agents/ imports.
# They trigger AWS AgentCore remotely via boto3 instead of running
# Strands orchestration locally on the Render web server.
# ==========================================
import boto3
import os

def _invoke_remote_agent(prompt: str) -> bool:
    """Trigger AWS AgentCore remotely if configured with a valid deployed runtime ARN or agent ID."""
    if os.environ.get("USE_REMOTE_AGENTCORE", "false").lower() not in ("true", "1"):
        return False

    runtime_arn = os.environ.get("AGENTCORE_RUNTIME_ARN") or os.environ.get("AGENTCORE_AGENT_ID")
    if not runtime_arn or runtime_arn == "default_agent_id":
        return False

    # Check if this is an AgentCore runtime ARN
    if "bedrock-agentcore" in runtime_arn or "runtime/" in runtime_arn:
        try:
            from botocore.config import Config
            config_boto = Config(read_timeout=60, connect_timeout=10, retries={"max_attempts": 1})
            client = boto3.client("bedrock-agentcore", region_name=os.environ.get("AWS_REGION", "us-east-1"), config=config_boto)
            payload_data: dict[str, Any] = {"inputText": prompt}
            mcp_url = os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("RENDER_MCP_URL") or "https://grantscout-api.onrender.com/mcp"
            payload_data["mcpUrl"] = mcp_url
            res = client.invoke_agent_runtime(
                agentRuntimeArn=runtime_arn,
                payload=json.dumps(payload_data).encode("utf-8")
            )
            body_bytes = res.get("response").read()
            body_str = body_bytes.decode("utf-8")
            try:
                body_json = json.loads(body_str)
                out = body_json.get("output", "")
            except Exception:
                out = body_str
            if "Agent Error:" in out or ("Error" in out and len(out) < 200):
                logger.error(f"Remote AgentCore returned error: {out}")
                return False
            logger.info(f"Remote AgentCore completed: {out[:100]}")
            return True
        except Exception as e:
            logger.error(f"Remote AgentCore trigger failed: {e}")
            return False
    else:
        # Legacy Bedrock Agent fallback
        try:
            bedrock_agent = boto3.client("bedrock-agent-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
            agent_alias_id = os.environ.get("AGENTCORE_AGENT_ALIAS_ID", "TSTALIASID")
            session_id = str(uuid.uuid4())
            bedrock_agent.invoke_agent(
                agentId=runtime_arn,
                agentAliasId=agent_alias_id,
                sessionId=session_id,
                inputText=prompt,
            )
            return True
        except Exception as e:
            logger.error(f"Remote agent trigger failed: {e}")
            return False


def draft_application_for_grant(grant: dict, callback=None) -> dict[str, Any]:
    """Draft application proposal using authentic Strands SDK 5-Agent Collaborative Swarm."""
    if _invoke_remote_agent(f"Draft application for grant {grant.get('grant_id')}"):
        return {"status": "triggered_remotely"}

    from agentcore.src.agents.drafter import draft_application_structured
    draft_result = draft_application_structured(grant, status_callback=callback)
    gid = grant.get("grant_id") or f"grants-gov-{grant.get('id')}"
    return {"status": "completed", "grant_id": gid, "draft": draft_result.model_dump()}


async def run_orchestrator(remote_tools=None, status_callback=None) -> dict[str, Any]:
    """Run discovery and scoring orchestration using authentic Strands SDK GraphBuilder DAG."""
    if _invoke_remote_agent("Run grant scan and orchestration"):
        if status_callback:
            status_callback("AWS AgentCore multi-agent swarm completed scan & scoring in cloud.")
        grants = storage.list_grants()
        if len(grants) > 0:
            return {
                "status": "completed",
                "grants_scanned": len(grants),
                "result_preview": f"AgentCore Swarm completed. {len(grants)} grants active.",
            }
        logger.info("Remote agent returned 0 grants; executing local engine.")

    from agentcore.src.agents.orchestrator import run_full_orchestration_cycle as execute_graph_cycle
    return await execute_graph_cycle(
        remote_tools=remote_tools,
        status_callback=status_callback,
    )


async def run_full_orchestration_cycle(*args, **kwargs) -> dict[str, Any]:
    return await run_orchestrator(*args, **kwargs)


def run_deadline_check(*args, **kwargs):
    if _invoke_remote_agent("Check upcoming deadlines"):
        return {"status": "remote_check_triggered"}
    from backend.tools.notifications import scan_upcoming_deadlines
    return scan_upcoming_deadlines()


def score_grant(grant: dict, profile: dict | None = None) -> dict[str, Any]:
    """Evaluate a single grant opportunity using the authentic Matcher Agent."""
    from agentcore.src.agents.matcher import evaluate_grant_structured
    evaluation = evaluate_grant_structured(grant, persist=True)
    return evaluation.model_dump()

# ==========================================

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


async def _background_scan_loop():
    """Autonomous background scan loop — runs the full pipeline on a recurring interval.

    Grants.gov updates once daily, so the default interval is 24 hours.
    Override with SCAN_INTERVAL_HOURS env var (e.g., 0.01 for 36s demo cycles).
    """
    interval_seconds = config.SCAN_INTERVAL_HOURS * 3600
    logger.info(f"🔄 Background auto-scan enabled. Interval: every {config.SCAN_INTERVAL_HOURS}h")

    # Wait before first scan to let the server fully initialize
    await asyncio.sleep(30)

    while True:
        try:
            logger.info("🚀 Background auto-scan starting...")
            await broadcast_event({
                "event": "auto_scan_started",
                "data": json.dumps({"message": "Autonomous background scan initiated"}),
            })

            # Decoupled: uses stub run_full_orchestration_cycle() defined above
            result = await run_full_orchestration_cycle()

            grants_found = result.get("grants_scanned", 0)
            logger.info(f"✅ Background auto-scan complete. {grants_found} grants processed.")

            # Dispatch background drafting tasks for high-scoring opportunities
            dispatch_queued_drafts()

            await broadcast_event({
                "event": "auto_scan_completed",
                "data": json.dumps({
                    "message": f"Background scan complete: {grants_found} grants processed",
                    "grants_scanned": grants_found,
                    "status": "completed",
                }),
            })
        except Exception as e:
            logger.error(f"❌ Background auto-scan failed: {e}")

        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle handler."""
    logger.info("🚀 GrantScout API starting up...")
    logger.info(f"   Storage: Local ({config.LOCAL_STORAGE_PATH})")
    logger.info(f"   Model: {config.BEDROCK_MODEL_ID}")
    logger.info(f"   Security: {'Enabled (JWT + API Key)' if config.AUTH_ENABLED else 'Disabled (Dev Mode)'}")
    # Ensure default organization profile exists
    if not storage.get_org_profile("default"):
        from backend.storage.personas import PERSONAS, persona_to_org_profile
        default_profile = persona_to_org_profile(PERSONAS[0])
        storage.save_org_profile(default_profile.model_dump())
        logger.info("🌱 Seeded default organization profile: Youth Education Alliance")

    # Start background autonomous scan task
    scan_task: asyncio.Task[Any] | None = None
    if config.AUTO_SCAN_ENABLED:
        scan_task = asyncio.create_task(_background_scan_loop())

    yield

    # Graceful shutdown
    if scan_task:
        scan_task.cancel()
        try:
            await scan_task
        except asyncio.CancelledError:
            pass
    logger.info("GrantScout API shutting down...")


app = FastAPI(
    title="GrantScout API",
    description="AI-powered autonomous grant discovery for small nonprofits",
    version="1.0.0",
    lifespan=lifespan,
)

# Security Headers Middleware (Pure ASGI to prevent SSE streaming body assertion errors)
from starlette.datastructures import MutableHeaders

class SecurityHeadersMiddleware:
    """Inject hardened HTTP security headers into all responses without breaking SSE streams."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["X-XSS-Protection"] = "1; mode=block"
                headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            await send(message)

        await self.app(scope, receive, send_wrapper)

app.add_middleware(SecurityHeadersMiddleware)


# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
#  Model Context Protocol (MCP) Server
# ──────────────────────────────────────────────
from backend.mcp_endpoints.server import mcp_server
app.mount("/mcp", mcp_server.sse_app())

# ──────────────────────────────────────────────
#  Authentication Endpoints
# ──────────────────────────────────────────────
from pydantic import BaseModel
from backend.security.auth import create_access_token


class TokenExchangeRequest(BaseModel):
    api_key: str
    org_id: str = "default"
    client_name: str = "frontend-client"


@app.post("/api/auth/token")
async def exchange_token(body: TokenExchangeRequest):
    """Exchange API key for a signed JWT access token."""
    if body.api_key != config.MASTER_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    token = create_access_token(
        data={
            "sub": body.client_name,
            "org_id": body.org_id,
            "role": "admin",
            "scopes": ["read", "write", "agent:execute"],
        }
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in_seconds": config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@app.get("/api/auth/verify")
async def verify_auth(auth: TokenPayload = Depends(get_current_auth)):
    """Verify current authentication credentials."""
    return {
        "authenticated": True,
        "identity": {
            "subject": auth.sub,
            "org_id": auth.org_id,
            "role": auth.role,
            "scopes": auth.scopes,
        },
    }

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


@app.get("/api/documents/{doc_name:path}")
async def get_knowledge_base_document(doc_name: str):
    """Retrieve full content and metadata for a specific indexed document."""
    doc = knowledge_base.get_document(doc_name)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_name}' not found")
    return doc


@app.post("/api/documents/index")
async def index_document(
    payload: dict,
    auth: TokenPayload = Depends(get_current_auth),
):
    """Index or update a document into the RAG Knowledge Base (Authenticated)."""
    doc_name = payload.get("doc_name", "").strip()
    content = payload.get("content", "").strip()
    category = payload.get("category", "general")

    if not doc_name or not content:
        raise HTTPException(status_code=400, detail="doc_name and content are required")

    chunks_indexed = knowledge_base.add_document(doc_name, content, category)

    storage.add_activity({
        "event_type": "document_indexed",
        "message": f"Indexed '{doc_name}' ({chunks_indexed} chunks) into Knowledge Base (by {auth.sub})",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    await broadcast_event({
        "type": "document_indexed",
        "doc_name": doc_name,
        "category": category,
        "chunks": chunks_indexed,
        "message": f"Document '{doc_name}' indexed successfully ({chunks_indexed} chunks)",
    })

    return {"status": "indexed", "doc_name": doc_name, "chunks": chunks_indexed, "indexed_by": auth.sub}


@app.delete("/api/documents/{doc_name:path}")
async def delete_knowledge_base_document(
    doc_name: str,
    auth: TokenPayload = Depends(get_current_auth),
):
    """Delete a document and its embeddings from the RAG Knowledge Base (Authenticated)."""
    success = knowledge_base.delete_document(doc_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Document '{doc_name}' not found")

    storage.add_activity({
        "event_type": "document_deleted",
        "message": f"Deleted document '{doc_name}' from Knowledge Base (by {auth.sub})",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    await broadcast_event({
        "type": "document_deleted",
        "doc_name": doc_name,
        "message": f"Document '{doc_name}' removed from Knowledge Base",
    })

    return {"status": "deleted", "doc_name": doc_name, "deleted_by": auth.sub}


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
    """Trigger the Drafter Agent to synthesize a 6-section grant application (Authenticated)."""
    grant = storage.get_grant(grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")

    # Update grant status
    grant["status"] = "drafting"
    grant["is_drafting"] = True
    storage.save_grant(grant)

    # Broadcast start
    await broadcast_event({
        "type": "drafting_started",
        "message": "INITIALIZING DRAFTER SWARM...",
        "grant_id": grant_id,
    })

    loop = asyncio.get_running_loop()

    def on_agent_thought(msg: str):
        asyncio.run_coroutine_threadsafe(
            broadcast_event({
                "type": "agent_thought",
                "message": msg,
                "grant_id": grant_id,
            }),
            loop,
        )

    try:
        # Run authentic Bedrock synthesis in threadpool to allow concurrent SSE event streaming
        await asyncio.to_thread(draft_application_for_grant, grant, on_agent_thought)

        # Retrieve created application
        apps = storage.list_applications()
        matched_app = next((a for a in apps if a.get("grant_id") == grant_id), None)
        if not matched_app or not matched_app.get("sections"):
            raise RuntimeError("Drafter completed without producing valid sections in storage.")

        grant["status"] = "ready_for_review"
        grant["is_drafted"] = True
        grant["is_drafting"] = False
        grant["draft_id"] = matched_app.get("draft_id")
        storage.save_grant(grant)

        await broadcast_event({
            "type": "application_drafted",
            "message": f"Draft proposal ready for '{grant.get('title')}'",
            "grant_id": grant_id,
            "draft_id": matched_app.get("draft_id"),
        })

        return {
            "status": "completed",
            "application": matched_app,
            "draft_id": matched_app.get("draft_id"),
            "requested_by": auth.sub,
        }

    except Exception as e:
        logger.error(f"Drafting failed: {e}")
        # Rollback partial draft
        apps = storage.list_applications()
        matched_app = next((a for a in apps if a.get("grant_id") == grant_id), None)
        if matched_app and matched_app.get("draft_id"):
            storage.delete_application(matched_app["draft_id"])

        grant["status"] = "matched"
        grant["is_drafting"] = False
        grant["is_drafted"] = False
        storage.save_grant(grant)

        await broadcast_event({
            "type": "drafting_failed",
            "grant_id": grant_id,
            "message": f"Auto-drafting failed for '{grant.get('title')}': {e!s}",
        })
        raise HTTPException(status_code=500, detail=f"AI Proposal Drafting Failed: {e!s}")


# ──────────────────────────────────────────────
#  Agent Control Endpoints & Background Workers
# ──────────────────────────────────────────────


def execute_background_drafting(grant_id: str, loop: asyncio.AbstractEventLoop):
    """Synchronous background worker that executes the Drafter Agent swarm securely."""
    grant = storage.get_grant(grant_id)
    if not grant:
        logger.warning(f"Background drafting: grant {grant_id} not found in storage.")
        return

    title = grant.get("title", "Grant Opportunity")
    logger.info(f"🚀 Starting autonomous background drafting swarm for grant {grant_id}: '{title}'")

    try:
        # Decoupled: uses stub draft_application_for_grant() defined above

        grant["status"] = "drafting"
        grant["is_drafting"] = True
        storage.save_grant(grant)

        asyncio.run_coroutine_threadsafe(
            broadcast_event({
                "type": "drafting_started",
                "grant_id": grant_id,
                "title": title,
                "message": f"Autonomous AI Drafter swarm started for '{title}'...",
            }),
            loop
        )

        def on_agent_thought(msg: str):
            asyncio.run_coroutine_threadsafe(
                broadcast_event({
                    "type": "agent_thought",
                    "message": msg,
                    "grant_id": grant_id,
                }),
                loop,
            )

        # Run multi-agent drafting swarm synchronously in the background thread
        result = draft_application_for_grant(grant, on_agent_thought)

        apps = storage.list_applications()
        matched_app = next((a for a in apps if a.get("grant_id") == grant_id), None)

        grant["status"] = "ready_for_review"
        grant["is_drafted"] = True
        grant["is_drafting"] = False
        grant["draft_id"] = matched_app.get("draft_id") if matched_app else None
        storage.save_grant(grant)

        logger.info(f"✅ Background drafting completed successfully for {grant_id}")

        asyncio.run_coroutine_threadsafe(
            broadcast_event({
                "type": "application_drafted",
                "message": f"Draft proposal ready for '{title}'",
                "grant_id": grant_id,
                "draft_id": matched_app.get("draft_id") if matched_app else None,
            }),
            loop
        )

    except Exception as e:
        logger.error(f"❌ Background drafting failed for {grant_id}: {e}")
        apps = storage.list_applications()
        matched_app = next((a for a in apps if a.get("grant_id") == grant_id), None)
        if matched_app and matched_app.get("draft_id"):
            storage.delete_application(matched_app["draft_id"])

        grant["status"] = "matched"
        grant["is_drafting"] = False
        grant["is_drafted"] = False
        storage.save_grant(grant)
        asyncio.run_coroutine_threadsafe(
            broadcast_event({
                "type": "drafting_failed",
                "grant_id": grant_id,
                "message": f"Auto-drafting failed for '{title}': {e!s}",
            }),
            loop
        )


def dispatch_queued_drafts(background_tasks: BackgroundTasks | None = None, loop: asyncio.AbstractEventLoop | None = None) -> list[str]:
    """Find any grants in 'drafting' status without an existing completed draft and launch background workers."""
    grants = storage.list_grants()
    apps = storage.list_applications()
    drafted_grant_ids = {a.get("grant_id") for a in apps if a.get("grant_id")}

    if loop is None:
        loop = asyncio.get_running_loop()

    dispatched = []
    for g in grants:
        gid = g.get("grant_id") or g.get("id")
        if not gid:
            continue
        if (g.get("status") == "drafting" or g.get("is_drafting")) and gid not in drafted_grant_ids:
            dispatched.append(gid)
            if background_tasks:
                background_tasks.add_task(execute_background_drafting, gid, loop)
            else:
                loop.run_in_executor(None, execute_background_drafting, gid, loop)

    if dispatched:
        logger.info(f"⚡ Dispatched {len(dispatched)} autonomous background drafting task(s): {dispatched}")
    return dispatched


@app.post("/api/agent/scan")
async def trigger_scan(
    background_tasks: BackgroundTasks,
    auth: TokenPayload = Depends(get_current_auth)
):
    """Manually trigger a grant scan (Authenticated)."""
    try:
        # Decoupled: uses stub run_orchestrator() defined above

        storage.add_activity({
            "event_type": "scan_started",
            "message": f"Grant scan initiated across federal databases (by {auth.sub})...",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        await broadcast_event({
            "type": "scan_started",
            "message": "Grant scan initiated...",
        })

        loop = asyncio.get_running_loop()
        def on_agent_thought(msg: str):
            asyncio.run_coroutine_threadsafe(
                broadcast_event({
                    "type": "agent_thought",
                    "message": msg,
                }),
                loop
            )

        result = await run_orchestrator(status_callback=on_agent_thought)

        # Dispatch background drafting for any high-scoring grants discovered securely
        loop = asyncio.get_running_loop()
        queued_drafts = dispatch_queued_drafts(background_tasks, loop)

        storage.add_activity({
            "event_type": "scan_completed",
            "message": f"Grant scan completed successfully. {len(queued_drafts)} proposals queued for background drafting.",
            "details": {"result_preview": str(result)[:200] if result else "", "queued_drafts": queued_drafts},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        await broadcast_event({
            "type": "scan_completed",
            "message": "Grant scan completed!",
            "queued_drafts": queued_drafts,
        })

        return {"status": "completed", "result": result, "queued_drafts": queued_drafts, "triggered_by": auth.sub}

    except Exception as e:
        logger.error(f"Scan failed: {e}")
        storage.add_activity({
            "event_type": "error",
            "message": f"Grant scan failed: {e!s}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        # Broadcast the failure so the UI can display a toast
        asyncio.run_coroutine_threadsafe(
            broadcast_event({
                "type": "scan_failed",
                "message": f"Scan failed: {e!s}"
            }),
            asyncio.get_running_loop()
        )
        
        raise HTTPException(status_code=500, detail=f"Scan failed: {e!s}")


@app.post("/api/agent/orchestrate")
async def trigger_full_orchestration(auth: TokenPayload = Depends(get_current_auth)):
    """Trigger the complete autonomous Orchestrator cycle (Authenticated)."""
    try:
        # Decoupled: uses stub run_full_orchestration_cycle() defined above

        storage.add_activity({
            "event_type": "scan_started",
            "message": f"Full autonomous orchestration cycle running in background (triggered by {auth.sub})...",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        summary = await run_full_orchestration_cycle()

        # Dispatch background drafting for high-scoring grants
        queued_drafts = dispatch_queued_drafts()

        await broadcast_event({
            "type": "orchestration_completed",
            "message": f"Autonomous cycle finished: {summary.get('grants_scanned', 0)} opportunities processed, {len(queued_drafts)} queued for drafting",
            "queued_drafts": queued_drafts,
        })

        return {"status": "completed", "summary": summary, "queued_drafts": queued_drafts, "triggered_by": auth.sub}

    except Exception as e:
        logger.error(f"Orchestration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Orchestration failed: {e!s}")


@app.post("/api/agent/deadlines")
async def trigger_deadline_check(auth: TokenPayload = Depends(get_current_auth)):
    """Trigger a deadline monitoring sweep across active opportunities (Authenticated)."""
    try:
        # Decoupled: uses stub run_deadline_check() defined above

        summary = run_deadline_check()
        return {"status": "completed", "summary": summary, "triggered_by": auth.sub}

    except Exception as e:
        logger.error(f"Deadline sweep failed: {e}")
        raise HTTPException(status_code=500, detail=f"Deadline sweep failed: {e!s}")


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

        # Decoupled: uses stub score_grant() defined above

        result = score_grant(grant)
        return {"status": "scored", "result": result, "triggered_by": auth.sub}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scoring failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scoring failed: {e!s}")


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
        "auto_scan_enabled": config.AUTO_SCAN_ENABLED,
    }


@app.get("/api/agent/autoscan/status")
async def get_autoscan_status():
    """Return the current background auto-scan configuration."""
    return {
        "enabled": config.AUTO_SCAN_ENABLED,
        "interval_hours": config.SCAN_INTERVAL_HOURS,
        "next_scan_note": f"Every {config.SCAN_INTERVAL_HOURS} hours" if config.AUTO_SCAN_ENABLED else "Disabled",
    }


# ──────────────────────────────────────────────
#  Health Check
# ──────────────────────────────────────────────


@app.get("/health")
@app.get("/healthz")
@app.get("/api/health")
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

from pydantic import BaseModel

from backend.storage.personas import PERSONAS, get_persona_by_id, persona_to_org_profile
from backend.tools.compliance import audit_application_compliance


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
    payload: ComplianceAuditRequest | None = None,
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
    AGENT_TIER_MAP,
    MODEL_TIERS,
    response_cache,
    token_tracker,
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


# ──────────────────────────────────────────────
#  Admin / Cache Purge Endpoints
# ──────────────────────────────────────────────


@app.post("/api/admin/clear-cache")
async def clear_system_cache(auth: TokenPayload = Depends(get_current_auth)):
    """Clear all cached responses, stored grants, applications, and activity records (Authenticated)."""
    # 1. Clear in-memory response cache
    response_cache.clear()

    # 2. Clear stored grants, applications, and activity
    purge_summary = storage.purge_all_data()

    logger.info(f"System cache and stored data cleared by {auth.sub}: {purge_summary}")

    # Broadcast event to frontend to refresh
    await broadcast_event({
        "type": "cache_cleared",
        "message": "All cached data, grants, and activity purged successfully",
    })

    return {
        "status": "cleared",
        "purged": purge_summary,
        "cache_stats": response_cache.stats,
        "cleared_by": auth.sub,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,
    )

