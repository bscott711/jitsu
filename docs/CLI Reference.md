# Jitsu CLI Reference

Jitsu provides a minimalist CLI built on top of `typer` to manage the orchestration server.

## `jitsu serve`

**Description:**
Starts the Jitsu MCP Server over `stdio`. This is the primary mode of operation for integration with AI IDEs.

- **Usage**: `jitsu serve` (Usually configured directly in the IDE's MCP settings).
- **Flags**:
  - `--epic` / `-e`: (Optional) Path to a JSON Epic plan to preload into the queue.
  - `--help`: Show the command-specific help message.

---

## Global Options
