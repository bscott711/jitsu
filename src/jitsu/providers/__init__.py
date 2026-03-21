"""
Jitsu Context Providers package.

This module houses the base interface and all concrete implementations
for resolving JIT context targets into LLM-optimized strings.
"""

from jitsu.providers.ast import ASTProvider, ASTTransformer
from jitsu.providers.base import BaseProvider
from jitsu.providers.env import EnvVarProvider
from jitsu.providers.file import FileStateProvider
from jitsu.providers.git import GitProvider
from jitsu.providers.markdown import MarkdownASTProvider
from jitsu.providers.pydantic import PydanticProvider
from jitsu.providers.registry import ProviderRegistry
from jitsu.providers.tree import DirectoryTreeProvider

__all__ = [
    "ASTProvider",
    "ASTTransformer",
    "BaseProvider",
    "DirectoryTreeProvider",
    "EnvVarProvider",
    "FileStateProvider",
    "GitProvider",
    "MarkdownASTProvider",
    "ProviderRegistry",
    "PydanticProvider",
]
