"""LKIO MCP Server Entrypoint for Cursor IDE and External AI Agents."""

from pathlib import Path
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.mcp.server import LKIO_MCPServer

if __name__ == "__main__":
    server = LKIO_MCPServer()
    server.run_stdio()
