"""Template loading utilities for Jitsu."""

import importlib.resources


class TemplateLoader:
    """Utility class to load static templates from the package."""

    @staticmethod
    def load_template(filename: str) -> str:
        """Load a template file from the jitsu.templates package."""
        return (
            importlib.resources.files("jitsu.templates")
            .joinpath(filename)
            .read_text(encoding="utf-8")
        )
