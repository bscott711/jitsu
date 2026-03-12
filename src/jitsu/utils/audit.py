"""
Generate V2 Audit Reports for Jitsu Modules.

Runs Vulture, Complexipy, Ruff, and Pyright, and hunts for inline ignores.
"""

import subprocess
from datetime import datetime, timezone
from pathlib import Path

import typer

# Assuming this file is at src/jitsu/utils/audit.py, parents[3] is the project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "docs" / "audit_v2"
MODULES_TO_AUDIT = [
    "src/jitsu/core",
    "src/jitsu/cli",
    "src/jitsu/models",
    "src/jitsu/providers",
    "src/jitsu/server",
]

IGNORES_TO_HUNT = ["# n" + "oqa", "# t" + "ype: ignore", "# py" + "right: ignore"]


def run_command(cmd: list[str]) -> str:
    """Run a CLI command and return its combined stdout/stderr."""
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as e:
        return f"ERROR running command {' '.join(cmd)}: {e}"
    else:
        output = result.stdout.strip()
        if result.stderr.strip():
            output += f"\n{result.stderr.strip()}"
        return output or "No output (Clean pass!)"


def _scan_file_for_ignores(py_file: Path) -> list[str]:
    """Scan a single file for inline ignores."""
    file_hits: list[str] = []
    try:
        with py_file.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                if any(ignore in line for ignore in IGNORES_TO_HUNT):
                    # Strip whitespace but keep the content to show context
                    file_hits.append(
                        f"- **{py_file.relative_to(PROJECT_ROOT)}:{line_num}** ` {line.strip()} `"
                    )
    except (OSError, UnicodeDecodeError) as e:
        file_hits.append(f"- Error reading {py_file.name}: {e}")

    return file_hits


def hunt_for_ignores(module_path: Path) -> str:
    """Scan Python files for inline linting/typing ignores."""
    hits: list[str] = []
    for py_file in module_path.rglob("*.py"):
        hits.extend(_scan_file_for_ignores(py_file))

    if not hits:
        return "No inline ignores found! 🎉"
    return "\n".join(hits)


def main() -> None:
    """Execute the audit report generation."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    for module in MODULES_TO_AUDIT:
        module_path = PROJECT_ROOT / module
        if not module_path.exists():
            typer.secho(f"⚠️ Skipping {module} - Directory not found.", fg=typer.colors.YELLOW)
            continue

        module_name = module_path.name
        report_file = OUTPUT_DIR / f"{module_name}_audit_report.md"

        typer.secho(f"🔍 Auditing {module}...", fg=typer.colors.CYAN)

        report_content = [
            f"# V2 Audit Report: `{module}`",
            "",
            f"> **Generated:** {timestamp}",
            "",
            "## 1. Dead Code Analysis (Vulture)",
            "",
            "```text",
            run_command(["uv", "run", "vulture", module]),
            "```",
            "",
            "## 2. Cognitive Complexity (Complexipy)",
            "",
            "```text",
            run_command(["uv", "run", "complexipy", module]),
            "```",
            "",
            "## 3. Linting (Ruff)",
            "",
            "```text",
            run_command(["uv", "run", "ruff", "check", module]),
            "```",
            "",
            "## 4. Static Typing (Pyright)",
            "",
            "```text",
            run_command(["uv", "run", "pyright", module]),
            "```",
            "",
            "## 5. Technical Debt (Inline Ignores)",
            "",
            hunt_for_ignores(module_path),
            "",
            "---",
            "",
            "*End of automated report.*",
        ]

        # MD047: Add the trailing newline explicitly at the end of the joined string
        report_file.write_text("\n".join(report_content) + "\n", encoding="utf-8")
        typer.secho(f"✅ Saved to {report_file.relative_to(PROJECT_ROOT)}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    main()
