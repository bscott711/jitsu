# **Jitsu Orchestration Pipeline & Roadmap**

*This document tracks the completed architectural milestones of Jitsu V2 (v0.2.0) and outlines the upcoming dogfooding roadmap for v0.3.0.*

## **✅ COMPLETED: v0.2.0 Architecture (The Jitsu V2 Engine)**

### **Milestone 1: The U-Curve Compiler (Attention Management)**

*Goal: Stop the model from "losing" instructions in the middle of massive file dumps.*

* **Phase 1.1: XML Tag Standardization.** Implemented strict XML string constants (\<INSTRUCTIONS\>, \<JIT\_CONTEXT\_MANIFEST\>, \<JIT\_CONTEXT\_DETAIL\>, \<PRIORITY\_RECAP\>, and \<TASK\_AND\_OUTPUT\_SPEC\>).  
* **Phase 1.2: The ContextCompiler Refactor.** Rewired src/jitsu/core/compiler.py to enforce the U-Curve structure. Read-only context (the "trough") is logically sorted into the middle, while instructions and definitions of done sit at the absolute edges.  
* **Phase 1.3: Prompt Validation Suite.** Updated tests to assert the exact generation and presence of these newly centralized tags from src/jitsu/prompts.py.

### **Milestone 2: Pydantic Gatekeepers (Anti-Laziness & Zero-Bypass)**

*Goal: Revoke the model's physical ability to generate placeholders or bypass linters.*

* **Phase 2.1: Placeholder Rejection.** Enforced strict schema validation on the output. The system actively intercepts and rejects common LLM lazy tokens (\# rest of code here, ..., // previous code), forcing a retry before touching the disk.  
* **Phase 2.2: Symmetrical Engineering & 100% Coverage.** The Executor strictly requires tests to accompany architectural changes.  
* **Phase 2.3: Zero-Bypass Purge.** Global eradication of \# noqa, \# type: ignore, and \# pyright: ignore. The engine naturally satisfies linters rather than hiding from them.

### **Milestone 3: The AST-Aware Recovery Loop (Self-Correction)**

*Goal: Prevent hallucination spirals when tests or linters fail.*

* **Phase 3.1: Failure Schema & Truncation.** Created the VerificationFailureDetails schema to cleanly capture just verify errors (Pytest/Ruff/Pyright), stripping noise and extracting the precise failure traceback.  
* **Phase 3.2: AST Context Injection.** Updated the recovery loop to dynamically resolve the Abstract Syntax Tree (AST) of the failing file.  
* **Phase 3.3: Recovery Execution.** If verification fails, the executor injects the \<VERIFICATION\_SUMMARY\> (traceback \+ structural AST outline) into the recovery prompt, forcing a minimal, surgical patch rather than a blind rewrite.

## **🚀 UPCOMING: v0.3.0 Dogfooding Roadmap (Building Jitsu with Jitsu)**

*Goal: Use the v0.2.0 autonomous engine to build out Jitsu's safe-failure and CLI ergonomics.*

### **Milestone 4: The Branch-and-Quarantine Protocol**

*Goal: Prevent STUCK execution states from corrupting the user's working tree.*

* **Phase 4.1: Sandbox Branching.** Update jitsu auto to immediately cut a temporary branch (e.g., jitsu-run/\<epic-id\>) before execution begins.  
* **Phase 4.2: Auto-Merge on Success.** If the Epic completes and passes just verify, seamlessly merge the changes back into the original working branch and delete the sandbox.  
* **Phase 4.3: Quarantine on Failure.** If Max Retries are hit (STUCK), commit the broken state to the temporary branch, check the user back out to their clean working tree, and output a terminal message pointing them to the quarantine branch for manual review.

### **Milestone 5: The Resume Command (jitsu resume)**

*Goal: Allow human-in-the-loop recovery for quarantined Epics.*

* **Phase 5.1: State File Hydration.** Build a CLI hook jitsu resume that reads the .state file left behind by a halted execution.  
* **Phase 5.2: Phase Advancement.** Allow the Orchestrator to detect if a human manually fixed the quarantined branch, mark the STUCK phase as COMPLETED, and seamlessly pick up the next phase in the Epic.

### **Milestone 6: Explicit Context Injection**

*Goal: Give the user surgical control over the LLM Planner's context payload.*

* **Phase 6.1: CLI Flag Integration.** Add \--include \<filepath\> and \--exclude \<filepath\> flags to the jitsu auto command.  
* **Phase 6.2: Manifest Override.** Force the Orchestrator to bypass or supplement the LLM's file discovery, statically injecting the requested files into the \<JIT\_CONTEXT\_MANIFEST\> from the very beginning of the Epic.