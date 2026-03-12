# **jitsu\_get\_next\_phase**

The jitsu\_get\_next\_phase tool is the primary entry point for AI agents to interact with Jitsu. It facilitates the **"Pull"** mechanism in the Jitsu workflow, allowing an agent to retrieve its next objective and the mathematically optimized "Just-In-Time" (JIT) context required to execute it safely.

## **🚀 Overview**

In a typical Jitsu-orchestrated workflow, the AI agent is not expected to know the entire project plan upfront. Instead, it operates in strictly bounded **Phases**. Each phase is defined by an AgentDirective.  
When an agent calls jitsu\_get\_next\_phase, Jitsu:

1. **Pops** the next available directive from its internal execution queue.  
2. **Compiles** the directive by resolving all requested context\_targets (files, ASTs, schemas, etc.).  
3. **Formats** the payload using our **U-Curve Architecture**, forcing critical instructions and Definitions of Done to the absolute edges of the prompt to eliminate LLM "Lost in the Middle" syndrome.

This ensures the agent always has the deterministic "Ground Truth" of the codebase at the exact moment it needs to act, preventing "Context Drift."

## **🛠 How It Works**

The tool sits at Layer 3 of the Jitsu Architecture and coordinates with several internal components:

### **1\. Queue Retrieval (JitsuStateManager)**

The server maintains an in-memory queue of pending work. jitsu\_get\_next\_phase retrieves the first item using a FIFO (First-In-First-Out) strategy. If no phases are pending, it returns a friendly "No pending phases" message.

### **2\. Context Compilation (ContextCompiler)**

The retrieved AgentDirective contains a list of context\_targets. The compiler iterates through these, using **Specialized Providers** to fetch the data:

* **ASTProvider (ast)**: Strips implementation details for Python files (saves \~80% tokens).  
* **PydanticProvider (pydantic)**: Extracts strict JSON schemas from live Python classes.  
* **DirectoryTreeProvider (tree)**: Generates visual file system maps.  
* **FileStateProvider (file)**: Reads raw, unadulterated file content.  
* **GitProvider (git)**: Reads git status and diffs.  
* **EnvVarProvider (env\_var)**: Safely provides environment state.  
* **MarkdownASTProvider (markdown\_ast)**: Extracts headings and code blocks.

### **3\. Progressive Disclosure**

If a phase is too large for a single prompt, or if the agent discovers it needs *more* context during execution, it can use the companion tool jitsu\_request\_context to supplement this initial pull.

## **📋 Technical Specification**

### **MCP Tool Definition**

* **Name**: jitsu\_get\_next\_phase  
* **Description**: "Get the next Jitsu phase directive to execute. This returns a U-Curve optimized prompt."  
* **Input Schema**:  
  {  
    "type": "object",  
    "properties": {}  
  }

### **Return Format (U-Curve Architecture)**

The tool returns a TextContent object containing a string highly structured with explicit XML boundaries. This is designed to prevent context decay:  
\<INSTRUCTIONS\>  
\*\*Epic:\*\* {epic\_id} | \*\*Phase:\*\* {phase\_id} | \*\*Scope:\*\* {module\_scope}

{instructions}

\#\#\# Anti-Patterns (STRICTLY FORBIDDEN)  
\- {pattern\_1}  
\- {pattern\_2}  
\</INSTRUCTIONS\>

\<JIT\_CONTEXT\_MANIFEST\>  
\- \`{target\_1}\`: \*\*Summarized (Structural AST)\*\* (ast)  
\- \`{target\_2}\`: \*\*Full Source\*\* (file)  
\</JIT\_CONTEXT\_MANIFEST\>

\<JIT\_CONTEXT\_DETAIL\>  
{Resolved Content from Providers goes here. This is the 'trough' of the U-Curve.}  
\</JIT\_CONTEXT\_DETAIL\>

\<PRIORITY\_RECAP\>  
You are executing Phase {phase\_id}. Adhere strictly to the anti-patterns and maintain zero linting bypasses.  
\</PRIORITY\_RECAP\>

\<TASK\_AND\_OUTPUT\_SPEC\>  
\#\#\# Completion Criteria  
\- \[ \] {criterion\_1}  
\- \[ \] {criterion\_2}

\#\#\# Verification Rule  
You MUST run the following commands to verify your work before reporting status:  
\`{verification\_commands}\`  
\</TASK\_AND\_OUTPUT\_SPEC\>

## **🔄 Sequence Diagram**

The following diagram illustrates the lifecycle of a jitsu\_get\_next\_phase call:  
sequenceDiagram  
    participant Agent  
    participant MCP as Jitsu MCP Server  
    participant Queue as StateManager  
    participant Compiler as ContextCompiler  
    participant Providers as ContextProviders

    Agent-\>\>MCP: jitsu\_get\_next\_phase()  
    MCP-\>\>Queue: get\_next\_directive()  
    Queue--\>\>MCP: AgentDirective  
    MCP-\>\>Compiler: compile\_directive(directive)  
    loop For each Target  
        Compiler-\>\>Providers: resolve(target\_id)  
        Providers--\>\>Compiler: Context Data  
    end  
    Compiler--\>\>MCP: U-Curve Compiled XML/Markdown Payload  
    MCP--\>\>Agent: Rich Execution Prompt

## **💡 Best Practices**

1. **Pull Early, Pull Often**: Call jitsu\_get\_next\_phase as your very first action when starting a task.  
2. **Respect the XML Boundaries**: The \<INSTRUCTIONS\> and \<TASK\_AND\_OUTPUT\_SPEC\> tags are absolute law. Do not hallucinate tasks outside of these boundaries.  
3. **No Placeholders**: Jitsu enforces strict Pydantic Gatekeepers. You must return 100% runnable code. // rest of code here will be instantly rejected by the orchestrator.  
4. **Run Verification**: Always execute the commands listed in the Verification section. If verification fails, Jitsu will automatically trigger its AST-aware recovery loop.  
5. **Handle Queue Empty**: If the tool returns "No pending phases," the current Epic is complete or hasn't been submitted yet. Use jitsu\_submit\_epic or the CLI to add work.