"""
Jitsu (実) - JIT Context & Workflow Orchestrator.

Main package initialization providing access to core server components.
"""

from jitsu.server.mcp_server import app, run_server

__all__ = ["app", "run_server"]
