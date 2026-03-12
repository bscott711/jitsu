# **CLI Command Reference**

Jitsu provides a powerful Typer-based CLI for managing your orchestration lifecycle, from initializing projects to starting background servers and submitting epics.

---

## **Core Commands**

### **`init`**

Scaffolds a new Jitsu project in the current working directory. It creates the necessary directory structure and configuration files to get started.

### **`serve`**

Starts the Jitsu MCP Server over stdio.

- **Options**:
  - `--epic`, `-e`: Path to a JSON Epic plan to preload into the queue.

### **`submit`**

Submits a new epic payload to a running Jitsu server over IPC.

- **Options**:
  - `--epic`, `-e`: Path to the epic JSON file (Required).

---

## **Queue Management**

### **`queue-ls`**

Lists all pending phases currently in the Jitsu queue.

### **`queue-clear`**

Clears all pending phases from the Jitsu queue.

---

## **Planning & Execution**

### **`plan`**

Generates a Jitsu plan from a natural language objective using an LLM.

- **Arguments**:
  - `objective`: The natural language objective (Required).
- **Options**:
  - `--file`, `-f`: Relevant files to provide as context (can be used multiple times).
  - `--out`, `-o`: Output path for the generated epic JSON (Default: `epic.json`).
  - `--model`, `-m`: The LLM model to use via OpenRouter.

### **`run`**

Generates a Jitsu plan and immediately submits it to the running server.

- **Arguments**:
  - `objective`: The natural language objective (Required).
- **Options**:
  - Same as `plan`.

### **`auto`**

Generates a Jitsu plan and executes it autonomously step-by-step.

- **Arguments**:
  - `objective`: The natural language objective.
- **Options**:
  - `--file`, `-f`: Load an existing Epic JSON file to resume execution.
  - `--context`, `-c`: Relevant files to provide as context.
  - `--model`, `-m`: The LLM model to use.
