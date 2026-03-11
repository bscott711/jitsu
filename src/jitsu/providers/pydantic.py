"""Pydantic V2 model schema context provider for Jitsu."""

import importlib
import json

from pydantic import BaseModel

from jitsu.providers.base import BaseProvider
from jitsu.utils.logger import get_logger

# F821 Fix: Define the logger at the module level
logger = get_logger(__name__)


class PydanticProvider(BaseProvider):
    """Provides the JSON schema of a specific Pydantic V2 model."""

    @property
    def name(self) -> str:
        """The unique name of this provider."""
        return "pydantic"

    async def resolve(self, target: str) -> str:
        """
        Dynamically load a Pydantic model and return its JSON schema.

        Args:
            target: The dot-formatted path to the class (e.g., 'jitsu.models.core.AgentDirective').

        Returns:
            str: A formatted Markdown block with the model's schema.

        """
        if "." not in target:
            return f"**ERROR:** Invalid Pydantic target '{target}'. Target must include at least one dot (e.g., 'package.Module.ClassName')."

        # Pyright Fix: Extract variables before the try block so they are
        # guaranteed to be bound if an exception occurs during import.
        module_path, class_name = target.rsplit(".", 1)

        try:
            module = importlib.import_module(module_path)
            model_class = getattr(module, class_name)

            if not isinstance(model_class, type) or not issubclass(model_class, BaseModel):
                return f"### [FAILED] Pydantic Schema: {target}\n**ERROR:** '{target}' is not a Pydantic V2 'BaseModel'."

            schema = model_class.model_json_schema()
            schema_json = json.dumps(schema, indent=2)

        except ImportError as e:
            msg = f"**ERROR:** Could not import module '{module_path}' for target '{target}': {e}"
            return f"### [FAILED] Pydantic Schema: {target}\n{msg}"
        except AttributeError as e:
            msg = f"**ERROR:** Class '{class_name}' not found in module '{module_path}': {e}"
            return f"### [FAILED] Pydantic Schema: {target}\n{msg}"
        except Exception as e:
            # Safely route the exception to stderr via our strict logger
            logger.exception("Unexpected error resolving pydantic model %s", target)
            msg = f"**ERROR:** An unexpected error occurred while resolving '{target}': {e}"
            return f"### [FAILED] Pydantic Schema: {target}\n{msg}"
        else:
            return f"### Pydantic Model Schema: {target}\n```json\n{schema_json}\n```"
