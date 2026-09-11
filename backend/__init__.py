# GrantScout Backend Package
import sys

# Force stdout and stderr to UTF-8 on Windows to prevent charmap UnicodeEncodeErrors during agent streaming
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from pathlib import Path

# Ensure agentcore/src is on sys.path so its internal modules (mcp_tools, agents, shared) resolve cleanly
_agentcore_src = str(Path(__file__).resolve().parent.parent / "agentcore" / "src")
if _agentcore_src not in sys.path:
    sys.path.insert(0, _agentcore_src)
