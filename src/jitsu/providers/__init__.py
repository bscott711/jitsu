"""
Jitsu Context Providers package.

This module houses the base interface and all concrete implementations
for resolving JIT context targets into LLM-optimized strings.
"""

from jitsu.providers.base import BaseProvider

__all__ = ["BaseProvider"]
