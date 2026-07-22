"""Pytest / contract-drift / git-coverage stage runners, split out of logic.run()
so the orchestrator isn't 3 inline try/except blocks deep."""

from __future__ import annotations
import re
import subprocess
from pathlib import Path

from ...schemas import Metrics, AgentNode, ToolNode
from departments.operations.tools.shared.tool_parser import _norm

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _strip_ansi(text: str) -> str:
    """Strip ANSI color escape codes so report output stays clean even if
    pytest is invoked with a color-forcing env var (e.g. FORCE_COLOR)."""
    return _ANSI_ESCAPE_RE.sub("", text)


def run_tests(computed_metrics: Metrics, project_root: Path, dept_name: str) -> None:
    try:
        cmd = [
            "pytest",
            "--import-mode=importlib",
            "-q",
            "--tb=line",
            "--color=no",
            f"departments/{dept_name}/tools",
            "departments/operations/tools",
        ]
        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
        stdout = _strip_ansi(result.stdout)

        failures = []
        for line in stdout.split("\n"):
            if line.startswith("FAILED ") or line.startswith("ERROR "):
                failures.append(line.strip())

        output_lines = [
            line.strip() for line in stdout.strip().split("\n") if line.strip()
        ]
        summary = (
            output_lines[-1] if output_lines else "No tests found or missing output."
        )
        if result.returncode != 0:
            computed_metrics.tool_test_results = f"FAILED: {summary}"
            computed_metrics.tool_test_failures = failures
        else:
            computed_metrics.tool_test_results = summary
    except Exception as e:
        computed_metrics.tool_test_results = f"Pytest execution failed: {e}"


def check_contract_drift(
    computed_metrics: Metrics, project_root: Path, tool_nodes: list[ToolNode]
) -> None:
    try:
        from departments.operations.tools.shared.contract_diff import run_all

        drifts = run_all(project_root)
        drift_data = []

        # Also map to tool_nodes
        tool_map = {t.name: t for t in tool_nodes}

        for d in drifts:
            if d.has_drift:
                drift_dict = {
                    "tool_name": d.tool_name,
                    "contract_path": d.contract_path,
                    "contract_schema": d.contract_schema,
                    "schema_only": sorted(d.schema_only),
                    "template_only": sorted(d.template_only),
                }
                drift_data.append(drift_dict)

                if d.tool_name in tool_map:
                    tool_map[d.tool_name].contract_drift = drift_dict

        computed_metrics.contract_drift = drift_data
    except Exception as e:
        print(f"[WARNING] Could not calculate contract drift: {e}")


def check_git_coverage(computed_metrics: Metrics, agents_dir: Path) -> None:
    try:
        from departments.operations.tools.validators.validate_git_coverage import (
            logic as validate_git_coverage_logic,
        )

        coverage_result = validate_git_coverage_logic.analyze(agents_dir)
        computed_metrics.git_coverage_findings = [
            {
                "category": f.category,
                "file_path": f.file_path,
                "message": f.message,
                "detail": f.detail,
            }
            for f in coverage_result.findings
        ]
    except Exception as e:
        print(f"[WARNING] Could not calculate git coverage findings: {e}")


def check_unknown_tools(agent_nodes: list[AgentNode], raw_tools: list[dict]) -> None:
    tools_by_key = {}
    for t in raw_tools:
        for key in t.get("match_keys", []) or [_norm(t["name"])]:
            tools_by_key[key] = t

    for agent in agent_nodes:
        # We also check regular agents, but user explicitly asked about subagents
        # The analyzer will just catch all of them.
        for tool_name in agent.uses_tools:
            # We can also check if it contains a subcommand like tool_name::subcmd
            base_tool = tool_name.split("::")[0] if "::" in tool_name else tool_name

            # SYSTEM TOOLS
            if base_tool in {"git", "EnterWorktree"}:
                continue

            if _norm(base_tool) not in tools_by_key:
                err = f"Unknown Tool Called: '{tool_name}' does not exist in the tool registry."
                agent.validation_errors.append(err)
                agent.validation_status = "error"
                agent.status = "UNKNOWN"


def _run_ruff(project_root: Path) -> str:
    try:
        res = subprocess.run(
            ["ruff", "check", "departments/"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            return "PASS"
        lines = res.stdout.splitlines()
        summary = [line for line in lines if line.startswith("Found ")]
        return summary[-1].strip() if summary else f"FAIL (exit {res.returncode})"
    except Exception as e:
        return f"ERROR: {e}"


def _run_black(project_root: Path) -> str:
    try:
        res = subprocess.run(
            ["black", "--check", "departments/"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            return "PASS"
        if res.returncode == 1:
            return "FAIL: Formatting needed"
        return f"FAIL: {res.stderr.strip()}"
    except Exception as e:
        return f"ERROR: {e}"


def _run_mypy(project_root: Path) -> str:
    try:
        res = subprocess.run(
            ["mypy", "--explicit-package-bases", "departments/"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            return "PASS"
        lines = res.stdout.splitlines()
        summary = [line for line in lines if line.startswith("Found ")]
        return summary[-1].strip() if summary else f"FAIL (exit {res.returncode})"
    except Exception as e:
        return f"ERROR: {e}"


def _check_max_lines(project_root: Path) -> str:
    try:
        max_lines = 300
        oversized_files = []
        for py_file in project_root.joinpath("departments").rglob("*.py"):
            if py_file.is_file():
                with open(py_file, "r", encoding="utf-8") as f:
                    lines = sum(1 for _ in f)
                    if lines > max_lines:
                        oversized_files.append(f"{py_file.name} ({lines} lines)")
        if oversized_files:
            return f"FAIL: {len(oversized_files)} files > {max_lines} lines"
        return "PASS"
    except Exception as e:
        return f"ERROR: {e}"


def run_python_linters(computed_metrics: Metrics, project_root: Path) -> None:
    computed_metrics.python_linter_results = {
        "ruff": _run_ruff(project_root),
        "black": _run_black(project_root),
        "mypy": _run_mypy(project_root),
        "max-lines": _check_max_lines(project_root),
    }
