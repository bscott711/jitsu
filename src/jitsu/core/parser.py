"""Fuzzy XML/Markdown parser for extracting LLM outputs reliably."""

import re
import uuid

from jitsu.models.core import (
    AgentDirective,
    ContextTarget,
    EpicBlueprint,
    PhaseBlueprint,
    TargetResolutionMode,
)


class JitsuFuzzyParser:
    """Extracts structured data safely from XML-tagged LLM output."""

    @staticmethod
    def extract_tag(text: str, aliases: list[str], default: str = "") -> str:
        """
        Extract content from an XML-like tag.
        Handles missing closing tags and prevents truncation on nested <brackets>.
        """
        tag_group = "|".join(aliases)

        # 1. Try to find the explicit closing tag first (Safest for nested <brackets> like <module>)
        strict_pattern = rf"<\s*(?:{tag_group})\s*>(.*?)<\s*/\s*(?:{tag_group})\s*>"
        match = re.search(strict_pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()

        # 2. Fallback: Missing closing tag.
        # Stop at the next MAJOR known tag or EOF. Do NOT stop at random <words>.
        major_tags = "phase_id|description|module_scope|instructions|context_targets|anti_patterns|verification_commands|completion_criteria"
        fallback_pattern = rf"<\s*(?:{tag_group})\s*>(.*?)(?=<\s*/?(?:{major_tags})\s*>|$)"

        match = re.search(fallback_pattern, text, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else default

    @classmethod
    def parse_blueprint(cls, text: str) -> EpicBlueprint:
        """Extract the macro blueprint (Pass 1)."""
        epic_id = cls.extract_tag(text, ["epic_id", "epic", "id"], f"epic-{uuid.uuid4().hex[:6]}")
        phases = []

        # Find all <phase> blocks
        phase_blocks = re.findall(r"<phase>(.*?)</phase>", text, re.IGNORECASE | re.DOTALL)

        for block in phase_blocks:
            pid = cls.extract_tag(block, ["phase_id", "id", "name"])
            desc = cls.extract_tag(block, ["description", "summary", "desc"])
            if pid:
                phases.append(PhaseBlueprint(phase_id=pid, description=desc))

        return EpicBlueprint(epic_id=epic_id, phases=phases)

    @classmethod
    def parse_directive(cls, text: str, epic_id: str, phase_id: str) -> AgentDirective:
        """Extract the micro directive (Pass 2)."""
        scope_raw = cls.extract_tag(text, ["module_scope", "scope"])
        scope_list = [s.strip() for s in scope_raw.split(",")] if scope_raw else []

        targets_raw = cls.extract_tag(text, ["context_targets", "targets", "files"])
        target_list = [t.strip() for t in targets_raw.split("\n") if t.strip()]

        context_targets = [
            ContextTarget(
                provider_name="file",
                target_identifier=t,
                is_required=True,
                resolution_mode=TargetResolutionMode.FULL_SOURCE,
            )
            for t in target_list
        ]

        anti_patterns = [
            a.strip().lstrip("-* ")
            for a in cls.extract_tag(text, ["anti_patterns", "anti_pattern"]).split("\n")
            if a.strip()
        ]
        verification = [
            v.strip()
            for v in cls.extract_tag(
                text, ["verification_commands", "verification", "tests"]
            ).split("\n")
            if v.strip()
        ]
        completion = [
            c.strip().lstrip("-* ")
            for c in cls.extract_tag(text, ["completion_criteria", "completion"]).split("\n")
            if c.strip()
        ]
        instructions = cls.extract_tag(
            text, ["instructions", "instruction", "steps"], "No instructions provided."
        )

        return AgentDirective(
            epic_id=epic_id,
            phase_id=phase_id,
            module_scope=scope_list,
            instructions=instructions,
            context_targets=context_targets,
            anti_patterns=anti_patterns,
            verification_commands=verification,
            completion_criteria=completion,
        )
