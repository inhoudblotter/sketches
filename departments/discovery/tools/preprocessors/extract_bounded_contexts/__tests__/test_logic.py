from pathlib import Path

import typer
from typer.testing import CliRunner

from departments.discovery.tools.preprocessors.extract_bounded_contexts.command import (
    extract_bounded_contexts_cmd,
)
from departments.discovery.tools.preprocessors.extract_bounded_contexts.schemas import (
    ExtractBoundedContextsInput,
)
from departments.discovery.tools.preprocessors.extract_bounded_contexts.logic import (
    execute,
)


def _write_summary(domains_dir: Path, domain: str, executive_summary="", imports=None):
    domain_dir = domains_dir / domain
    domain_dir.mkdir(parents=True, exist_ok=True)
    lines = [f'domain: "{domain}"', f'executive_summary: "{executive_summary}"']
    if imports:
        lines.append("imports:")
        for imp in imports:
            lines.append(f'  - from_domain: "{imp["from_domain"]}"')
            lines.append(f'    entity: "{imp["entity"]}"')
            if "reason" in imp:
                lines.append(f'    reason: "{imp["reason"]}"')
    (domain_dir / "summary.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_extract_contexts_builds_dependency_from_imports(tmp_path: Path):
    domains_dir = tmp_path / "domains"
    _write_summary(domains_dir, "core", executive_summary="Owns users")
    _write_summary(
        domains_dir,
        "billing",
        executive_summary="Handles invoices",
        imports=[
            {
                "from_domain": "core",
                "entity": "User",
                "reason": "attach invoice to owner",
            }
        ],
    )

    output_file = tmp_path / "bounded_contexts.yaml"
    input_data = ExtractBoundedContextsInput(
        domains_dir=str(domains_dir), output_file=str(output_file)
    )

    result = execute(input_data)

    assert {c.domain for c in result.contexts} == {"billing", "core"}

    billing_context = next(c for c in result.contexts if c.domain == "billing")
    assert len(billing_context.dependencies) == 1
    dep = billing_context.dependencies[0]
    assert dep.target_domain == "core"
    assert dep.data_exchanged == ["User"]
    assert dep.business_reason == "attach invoice to owner"

    core_context = next(c for c in result.contexts if c.domain == "core")
    assert core_context.dependencies == []

    assert output_file.exists()


def test_multiple_imports_from_same_domain_are_merged(tmp_path: Path):
    domains_dir = tmp_path / "domains"
    _write_summary(domains_dir, "core")
    _write_summary(
        domains_dir,
        "billing",
        imports=[
            {"from_domain": "core", "entity": "User", "reason": "ownership"},
            {"from_domain": "core", "entity": "Account", "reason": "billing target"},
        ],
    )

    output_file = tmp_path / "bounded_contexts.yaml"
    result = execute(
        ExtractBoundedContextsInput(
            domains_dir=str(domains_dir), output_file=str(output_file)
        )
    )

    billing_context = next(c for c in result.contexts if c.domain == "billing")
    assert len(billing_context.dependencies) == 1
    dep = billing_context.dependencies[0]
    assert dep.target_domain == "core"
    assert dep.data_exchanged == ["User", "Account"]
    assert "ownership" in dep.business_reason
    assert "billing target" in dep.business_reason


def test_domain_without_summary_yaml_is_not_a_context(tmp_path: Path):
    domains_dir = tmp_path / "domains"
    domains_dir.mkdir(parents=True)
    (domains_dir / "no_summary_here").mkdir()
    _write_summary(domains_dir, "billing")

    output_file = tmp_path / "bounded_contexts.yaml"
    result = execute(
        ExtractBoundedContextsInput(
            domains_dir=str(domains_dir), output_file=str(output_file)
        )
    )

    assert {c.domain for c in result.contexts} == {"billing"}


def test_cli_reports_malformed_yaml_cleanly_without_raw_traceback(tmp_path: Path):
    domains_dir = tmp_path / "domains" / "broken"
    domains_dir.mkdir(parents=True)
    (domains_dir / "summary.yaml").write_text(
        "domain: broken\n  imports: [unterminated\n", encoding="utf-8"
    )

    output_file = tmp_path / "bounded_contexts.yaml"
    app = typer.Typer()
    app.command()(extract_bounded_contexts_cmd)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [str(tmp_path / "domains"), str(output_file)],
    )

    assert result.exit_code == 1
    assert "Error extracting bounded contexts" in result.output
    assert "Traceback (most recent call last)" not in result.output
