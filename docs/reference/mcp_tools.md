# **MCP Tools Reference**

Jitsu exposes 8 core tools via the Model Context Protocol (MCP). These tools enable an AI agent to become a self-orchestrating collaborator.

---

## **Orchestration Tools**

### **`jitsu_get_next_phase`**

Retrieves the next atomic directive from the Jitsu queue.

- **Role**: The primary "pull" mechanism for the agent to receive work.

### **`jitsu_report_status`**

Submits a report upon completion of a phase.

- **Parameters**: `phase_id`, `status`, `agent_notes`, `artifacts_generated`, `verification_output`.
- **Role**: Validates the phase and triggers the next one in the queue.

### **`jitsu_inspect_queue`**

Returns the current state of the pending phase queue.

- **Role**: Allows the agent to see upcoming tasks and overall epic progress.

### **`jitsu_submit_epic`**

Allows the agent to submit a new multi-phase plan (Epic) dynamically.

- **Parameters**: `directives` (List of AgentDirectives).
- **Role**: Enables agents to plan their own future work.

---

## **Context & Intelligence**

### **`jitsu_request_context`**

On-demand request for specific codebase context.

- **Parameters**: `target_identifier`, `provider_name` (optional).
- **Role**: Supports **Progressive Disclosure**, allowing the agent to pull detail as needed.

### **`jitsu_get_planning_context`**

Retrieves a high-level overview of the repository (directory tree, .jitsurules) to help the agent plan an epic.

- **Role**: Used during the initial "Planning" phase of an autonomous loop.

---

## **Repository Management**

### **`jitsu_git_status`**

Returns a summary of the current git status (e.g., modified files).

- **Role**: Helps the agent track its own changes.

### **`jitsu_git_commit`**

Stages all changes and creates a verified git commit.

- **Parameters**: `message`, `sync` (boolean).
- **Role**: Enforces the project's commit standards and verification requirements.
