"""Centralized registry mapping provider names to their classes."""

from jitsu.providers.ast import ASTProvider
from jitsu.providers.base import BaseProvider
from jitsu.providers.env import EnvVarProvider
from jitsu.providers.file import FileStateProvider
from jitsu.providers.git import GitProvider
from jitsu.providers.markdown import MarkdownASTProvider
from jitsu.providers.pydantic import PydanticProvider
from jitsu.providers.tree import DirectoryTreeProvider

# Single source of truth: maps provider name strings to their concrete classes.
# Add new providers here to make them available throughout the system.
ProviderRegistry: dict[str, type[BaseProvider]] = {
    "file": FileStateProvider,
    "pydantic": PydanticProvider,
    "ast": ASTProvider,
    "tree": DirectoryTreeProvider,
    "directory_tree": DirectoryTreeProvider,
    "git": GitProvider,
    "env_var": EnvVarProvider,
    "markdown_ast": MarkdownASTProvider,
}
