"""AgentCore Entrypoint — Decoupled Reasoning Engine.

This is the main entry point for the AWS AgentCore container.
It connects to the Render MCP server over the network, downloads
the 15 tools, and runs the Strands orchestration graph.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any

# Add src/ to Python path so relative imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp import ClientSession
from mcp.client.sse import sse_client

import mcp_tools
from agents.orchestrator import run_full_orchestration_cycle

logger = logging.getLogger()
logger.setLevel(logging.INFO)


async def _invoke_agent(prompt: str, mcp_url: str):
    """Connect to Render MCP server and run the Strands orchestration."""
    try:
        # Normalize SSE URL: FastMCP mounts SSE transport at /sse
        if not mcp_url.endswith("/sse"):
            mcp_url = f"{mcp_url.rstrip('/')}/sse"

        logger.info(f"Connecting to MCP server at {mcp_url}...")
        async with sse_client(mcp_url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                # Store the session and current event loop globally for threadsafe tool execution
                loop = asyncio.get_running_loop()
                mcp_tools.set_mcp_session(session, loop=loop)

                # Verify connection
                tools_list = await session.list_tools()
                logger.info(f"Connected to MCP Server. Loaded {len(tools_list.tools)} tools.")

                # Intent routing: Check if prompt is for proposal drafting or discovery orchestration
                if "draft" in prompt.lower():
                    import re
                    from agents.drafter import draft_application_structured_async
                    grant_id_match = re.search(r"(?:grants-gov-)?[0-9]{5,10}", prompt)
                    gid = grant_id_match.group(0) if grant_id_match else "unknown"
                    if not gid.startswith("grants-gov-") and gid.isdigit():
                        gid = f"grants-gov-{gid}"
                    result = await draft_application_structured_async({"grant_id": gid})
                    return result.model_dump()
                else:
                    # Run the full discovery graph DAG
                    result = await run_full_orchestration_cycle(prompt=prompt)
                    return result

    except Exception as e:
        logger.error(f"Failed to execute agent loop: {e}")
        return f"Agent Error: {str(e)}"


# Create HTTP Web Server conforming to AWS Bedrock AgentCore HTTP protocol (Port 8080)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="GrantScout AgentCore Runtime")

@app.get("/ping")
async def ping():
    """AgentCore health check endpoint."""
    return {"status": "Healthy"}

@app.post("/invocations")
async def invocations(request: Request):
    """AgentCore primary interaction endpoint."""
    try:
        data = await request.json()
    except Exception:
        data = {}
    
    prompt = data.get("inputText", "Start full autonomous scan")
    mcp_url = data.get("mcpUrl") or os.environ.get("RENDER_MCP_URL", "http://localhost:8000/mcp")
    result = await _invoke_agent(prompt, mcp_url)
    return {"output": str(result)}


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AgentCore BYO Container Entrypoint (Lambda Handler)."""
    prompt = event.get("inputText", "Start full autonomous scan")
    mcp_url = event.get("mcpUrl") or os.environ.get("RENDER_MCP_URL", "http://localhost:8000/mcp")

    result = asyncio.run(_invoke_agent(prompt, mcp_url))

    return {
        "statusCode": 200,
        "body": json.dumps({"output": str(result)})
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    logger.info(f"Starting AgentCore HTTP runtime on 0.0.0.0:{port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
