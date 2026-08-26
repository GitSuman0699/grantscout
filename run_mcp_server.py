"""Launcher script for GrantScout Model Context Protocol (MCP) Server.

Usage with Claude Desktop, Cursor, or any MCP client:
In your Claude Desktop config (claude_desktop_config.json):
{
  "mcpServers": {
    "grantscout": {
      "command": "python",
      "args": ["<path-to-grantscout>/run_mcp_server.py"]
    }
  }
}
"""

import sys
from pathlib import Path

# Ensure root directory is on sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.mcp.server import main

if __name__ == "__main__":
    main()
