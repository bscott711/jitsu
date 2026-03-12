# Phase 01: Pydantic Provider Research

## Objective

Review core domain models in `src/jitsu/models/core.py` to ensure compatibility with the upcoming Pydantic V2 provider, specifically focusing on JSON schema generation for Enums, nested lists, and default values.

## Findings

### 1. Enum Handling

- **Model**: `PhaseStatus(str, Enum)`
- **Pydantic V2 Behavior**: Standard `str, Enum` is well-supported. `model_json_schema()` will correctly generate:

    ```json
    {
      "type": "string",
      "enum": ["PENDING", "RUNNING", "SUCCESS", "FAILED", "STUCK"]
    }
    ```

- **Note**: Inheriting from `str` ensures the value is treated as a string during serialization, which is ideal for LLM context.

### 2. Nested Lists and Objects

- **Model**: `AgentDirective` contains `list[ContextTarget]`.
- **Pydantic V2 Behavior**: Recursive and nested model resolution is robust in V2. `model_json_schema()` will typically use `$defs` for the `ContextTarget` reference, keeping the schema clean and DRY (Don't Repeat Yourself).

    ```json
    {
      "properties": {
        "context_targets": {
          "items": { "$ref": "#/$defs/ContextTarget" },
          "type": "array"
        }
      }
    }
    ```

### 3. Default Values

- **Model**: `ContextTarget` has `is_required: bool = True`.
- **Pydantic V2 Behavior**: Correctly identifies default values and marks them as optional in the schema where appropriate, or specifies `default` in the property definition.

### 4. Configuration

- **Model**: `PhaseReport` uses `model_config = ConfigDict(use_enum_values=True)`.
- **Pydantic V2 Behavior**: This ensures that when the report is serialized (e.g., to be sent via MCP), the enum values rather than the enum objects themselves are used. This is critical for interoperability with external systems that expect raw JSON.

## Conclusion

The current models in `src/jitsu/models/core.py` are fully compatible with standard Pydantic V2 schema generation utilities. No changes are required to the core models to support the proposed Pydantic provider.

## Next Steps

- Proceed to the implementation of the `PydanticProvider` in `src/jitsu/providers/pydantic.py`.
- Ensure the provider can dynamically load and resolve these models.
