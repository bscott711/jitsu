# **Jitsu (実)**

**JIT Context & Workflow Orchestrator for AI IDEs via MCP**  
Jitsu inverts the control loop of AI IDEs (Antigravity, Cursor, Windsurf). Instead of relying on stale Markdown files for agent instructions, Jitsu allows external Python orchestrators to serve mathematically verified, Just-In-Time (JIT) context directly into an agent's brain via the Model Context Protocol (MCP).

## **The Problem: Prompt Debt & Context Drift**

When using localized agent instructions (e.g., .agents/coder\_directive.md), the codebase evolves but the prompts remain static. This "Context Drift" causes strict agents to hallucinate, reference outdated database schemas, or fall into infinite Maker/Checker error loops.

## **The Solution**

Jitsu treats Agent Skills as ephemeral, compiled artifacts.

1. **Strict Directives:** You define your agent's task, allowed imports, and required context as a strict Pydantic V2 model.  
2. **Context Providers:** Jitsu dynamically parses your live Python codebase (AST, Pydantic schemas, ORM models) to gather the exact requested context.  
3. **MCP Transport:** The IDE agent calls a Jitsu MCP tool to receive its assignment. It receives a perfectly accurate, point-in-time snapshot of the code it needs to work on.

## **Installation**

Jitsu is built to be managed via uv for lightning-fast dependency resolution.  
uv venv  
source .venv/bin/activate  
uv pip install \-e .

## **Quick Start (Conceptual)**

### **1\. Define the Directive in Python**

from jitsu.core import JitsuServer  
from jitsu.models import AgentDirective, ContextTarget

directive \= AgentDirective(  
    module\_scope="src/auth",  
    task="Implement password reset endpoint.",  
    context\_targets=\[  
        ContextTarget(provider="pydantic\_v2", target="src.schemas.UserReset"),  
        ContextTarget(provider="file\_state", target="src/auth/utils.py")  
    \],  
    anti\_patterns=\["Do not use MD5. Use passlib/bcrypt."\]  
)

server \= JitsuServer()  
server.queue\_directive("epic-auth-01", directive)  
server.serve() \# Starts the stdio MCP server

### **2\. The IDE Trigger**

Inside your AI IDE, create a single saved workflow:  
*"Call the jitsu\_get\_next\_phase() MCP tool. Read the payload, execute the task using ONLY the provided compiled context, and call jitsu\_report\_status() when finished."*

## **Architecture**

Jitsu is built on an extensible **Provider Pattern**. It ships with native providers for Pydantic V2 and Python AST parsing, but allows developers to easily register custom providers (e.g., SQLAlchemy schema dumpers, Django ORM inspectors) specific to their domain.
