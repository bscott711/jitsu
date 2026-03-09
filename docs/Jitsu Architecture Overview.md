# **Jitsu: JIT Context & Workflow Orchestrator**

**Jitsu** (実 / "Truth/Substance") is an MCP (Model Context Protocol) server designed to eliminate "Prompt Debt" and "Context Drift" in AI IDEs.  
It acts as a bridge between an external Python orchestrator and sandboxed IDE agents (Antigravity, Cursor, Windsurf). Instead of relying on static .md files for agent instructions, Jitsu compiles the "ground truth" of your codebase Just-In-Time (JIT) and serves it directly to the agent's context window.

## **Core Philosophy**

1. **The Code is the Source of Truth:** Never ask an LLM to read a codebase and write documentation about it. Use Python's AST and reflection capabilities to extract the exact state of the code.  
2. **Strict Directives:** Agent instructions should be typed, validated data structures, not free-form text.  
3. **Inversion of Control:** The IDE agent should not decide what to do next. It should ask Jitsu for its next phase, execute it, and report back.

## **High-Level Architecture**

Jitsu operates on three primary layers:

### **1\. The Directive Engine (Pydantic V2)**

At the heart of Jitsu is the AgentDirective model. This is a strict Pydantic V2 schema that developers use to define a task. Because it is Pydantic, it validates that requested modules or context targets actually exist *before* the agent is ever spun up.

### **2\. The Context Compiler (The "JIT" Engine)**

When an agent requests a task, the Context Compiler reads the AgentDirective and triggers the necessary **Context Providers**.

* If the directive asks for the context of UserLoginModel, the Pydantic Provider extracts the live V2 JSON schema for that model.  
* The Compiler weaves these JSON schemas, AST dumps, and the textual instructions into a single, highly-optimized Markdown payload.

### **3\. The MCP Transport Layer**

Jitsu exposes a lightweight MCP server with specific tools for the IDE Agent:

* jitsu\_get\_next\_phase(): The agent calls this to receive its compiled JIT context and instructions.  
* jitsu\_report\_status(status: str, artifacts: dict): The agent calls this to report success, failure, or to trigger the Meta-Feedback loop if it is stuck.  
* jitsu\_request\_deep\_context(target: str): Allows the agent to dynamically request the schema of a model it discovers it needs during execution.

## **The Agent Loop (In the IDE)**

Once Jitsu is running locally, the developer only needs a single saved prompt/workflow in their IDE:  
*"Initialize connection via the Jitsu MCP server. Call jitsu\_get\_next\_phase() to receive your strict constraints and current codebase truth. Execute the instructions perfectly. Call jitsu\_report\_status() when complete."*
