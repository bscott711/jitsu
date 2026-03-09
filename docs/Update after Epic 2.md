# Lead Dev Debrief

Here is a debrief of exactly where we stand, what the immediate next steps are, and a proposed architectural solution to eliminate your friction point with the MCP server lifecycle.

1. Where We Are

We have successfully built the read operations of our JIT Context Engine.

Epic 1 (Pydantic): We can dynamically extract exact schema definitions.

Epic 2 (AST): We can extract lightweight structural skeletons of any file.

Both of these live in Layer 2 (Providers) and strictly adhere to our BaseProvider contract. They are fast, non-blocking (thanks to the anyio refactor), and safe from protocol corruption (stderr logging).

1. What is Immediately Next

Before we move to a new epic, we have to wire the ASTProvider into Layer 1.5 (Core & State).
Right now, the ContextCompiler (which actually builds the Markdown string sent to the agent) needs to know that when an AgentDirective requests the "ast" provider, it should route that request to our new class.

We need to:

Register "ast" in the ContextCompiler.

Do a quick end-to-end test by asking the agent to read an AST skeleton via the jitsu_get_next_phase MCP tool.

1. Solving the MCP Server Friction

You are 100% correct to call this out. If Jitsu requires a hard restart every time you author a new directive, it violates the core tenet of developer tooling: stay out of the way.

Currently, jitsu serve --epic file binds the MCP server to stdio and locks the queue to that single file. Because the IDE owns the stdio process, we cannot easily Ctrl+C and restart it without the IDE's MCP client crashing or requiring a manual reload.

To solve this elegantly without breaking our strict architectural boundaries, I propose we implement a Local IPC (Inter-Process Communication) Queue.

Here is how we design it:

The CLI Workflow

Instead of passing the epic to the serve command, we split the server initialization from the epic submission.

The IDE Command: uv run jitsu serve (Starts the server empty).

The Developer Command: uv run jitsu submit epics/epic3.json (Pushes new work to the running server).

The Architecture (Layer 1.5 & 3)

The Background Socket: When jitsu serve starts the MCP stdio server (Layer 3), it will also spawn a lightweight background daemon (e.g., an anyio task listening on a local TCP port like 127.0.0.1:8765 or a local Unix domain socket).

The Submit Command: We add a new Typer command to src/jitsu/cli/main.py. When you run jitsu submit file, it reads the JSON and fires a quick HTTP/TCP payload to that local socket.

The State Manager: The socket listener receives the payload, parses it into an AgentDirective, and appends it directly to the JitsuStateManager's internal async queue.

The Result

The IDE agent never loses its connection. When you run the submit command, the queue quietly rehydrates. The next time the IDE agent invokes jitsu_get_next_phase, it simply picks up the new instructions and keeps working.
