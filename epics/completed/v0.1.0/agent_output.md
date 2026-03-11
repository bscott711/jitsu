# I have completed the pydantic-provider-alpha epic. This epic involved researching and implementing a new JIT context provider that resolves Pydantic V2 models into their JSON schema representations for inclusion in agent directives

Key Accomplishments:
Research Phase: Confirmed that the core domain models (

AgentDirective
,

ContextTarget
, etc.) in

src/jitsu/models/core.py
 are fully compatible with Pydantic V2 schema generation.
Implementation:
Developed the

PydanticV2Provider
 in

src/jitsu/providers/pydantic.py
. This provider dynamically loads model classes using importlib and extracts their JSON schemas.
Integrated the new provider into the

ContextCompiler
 in

src/jitsu/core/compiler.py
, enabling the pydantic_v2 provider name for use in compilation.
Updated

src/jitsu/providers/
init
.py
 to correctly export the new provider.
Testing and Quality:
Added comprehensive integration tests in

tests/providers/test_pydantic.py
, covering success scenarios, invalid targets, and error handling.
Achieved 100% code coverage across the modified and new modules.
Verified that all existing tests in the codebase pass.
Final Verification Results:
python

## src/jitsu/providers/pydantic.py

class PydanticV2Provider(BaseProvider):
    @property
    def name(self) -> str:
        return "pydantic_v2"
    async def resolve(self, target: str) -> str:
        # Dynamic import and schema extraction logic...
For a detailed analysis of the compatibility research, see the
pydantic_provider_research.md
 artifact.
