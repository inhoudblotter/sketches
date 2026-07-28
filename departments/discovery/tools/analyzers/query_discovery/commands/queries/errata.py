import typer
from pathlib import Path
from typing import Dict, cast

from ...logic.errata import get_errata
from ...logic.patches import get_patches, get_patch_errata
from ...logic.queries.flows import get_flows_self_check, get_flows_self_check_summary
from ...logic.reports.core import get_toc, get_stats
from ...logic.orphans import get_coverage
from ...logic.domain_consistency import check_domain_consistency


def _print_or_empty(res: dict, print_yaml, empty_message: str) -> None:
    if not res:
        typer.echo(empty_message)
    else:
        print_yaml(res)


def _filter_by_domain(res: dict, domain: str) -> dict:
    return {k: v for k, v in res.items() if k == domain}


def _filter_by_epic(res: dict, epic: str) -> dict:
    filtered = {
        d: {s: items for s, items in sources.items() if s == epic}
        for d, sources in res.items()
    }
    return {d: s for d, s in filtered.items() if s}


def _build_self_check_report(workspace: Path) -> dict:
    stats = get_stats(workspace)
    global_epic_types: Dict[str, int] = {}
    for d_stats in stats.values():
        for et, count in d_stats.get("epic_types", {}).items():
            global_epic_types[et] = global_epic_types.get(et, 0) + count

    domain_consistency = check_domain_consistency(workspace)

    return {
        "toc": get_toc(workspace, cast(str, None)),
        "stats": stats,
        "global_epic_type_distribution": global_epic_types,
        "missing_mandatory_epics": get_coverage(workspace).get(
            "missing_mandatory_epics", {}
        ),
        "duplicate_entities": domain_consistency.get("duplicate_entities", {}),
        "orphaned_personas": domain_consistency.get("orphaned_personas", []),
        "open_errata": get_errata(workspace, "open", scope="domain"),
        "open_patches": get_patches(
            workspace, domain=cast(str, None), status="pending"
        ),
    }


def _run_errata_domain(workspace: Path, domain: str, status: str, print_yaml) -> None:
    res = get_errata(workspace, status, scope="domain")
    if domain:
        res = _filter_by_domain(res, domain)
    _print_or_empty(res, print_yaml, "No errata found.")


def _run_errata_epic(
    workspace: Path, domain: str, epic: str, status: str, print_yaml
) -> None:
    res = get_errata(workspace, status, scope="epic")
    if domain:
        res = _filter_by_domain(res, domain)
    if epic:
        res = _filter_by_epic(res, epic)
    _print_or_empty(res, print_yaml, "No errata found.")


def _run_errata_global(workspace: Path, domain: str, status: str, print_yaml) -> None:
    res = get_errata(workspace, status, scope="global")
    if domain:
        res = _filter_by_domain(res, domain)
    _print_or_empty(res, print_yaml, "No errata found.")


def register_errata_queries(app: typer.Typer, print_yaml):
    @app.command("errata-domain")
    def errata_domain(
        workspace: Path = typer.Argument(Path("workspace/")),
        domain: str = typer.Option(None, "--domain", "-d"),
        status: str = typer.Option("open", "--status", "-s"),
    ):
        _run_errata_domain(workspace, domain, status, print_yaml)

    @app.command("errata-epic")
    def errata_epic(
        workspace: Path = typer.Argument(Path("workspace/")),
        domain: str = typer.Option(None, "--domain", "-d"),
        epic: str = typer.Option(None, "--epic", "-e"),
        status: str = typer.Option("open", "--status", "-s"),
    ):
        _run_errata_epic(workspace, domain, epic, status, print_yaml)

    @app.command("errata-global")
    def errata_global(
        workspace: Path = typer.Argument(Path("workspace/")),
        domain: str = typer.Option(None, "--domain", "-d"),
        status: str = typer.Option("all", "--status", "-s"),
    ):
        _run_errata_global(workspace, domain, status, print_yaml)

    @app.command("patches-domain")
    def patches_domain(
        workspace: Path = typer.Argument(Path("workspace/")),
        domain: str = typer.Option(None, "--domain", "-d"),
        status: str = typer.Option("pending", "--status", "-s"),
    ):
        res = get_patches(workspace, domain, status)
        _print_or_empty(res, print_yaml, "No patches found.")

    @app.command("patch-errata-domain")
    def patch_errata_domain(
        patch: str = typer.Option(..., "--patch", "-p"),
        workspace: Path = typer.Argument(Path("workspace/")),
    ):
        res = get_patch_errata(workspace, patch)
        _print_or_empty(res, print_yaml, f"No errata linked to patch '{patch}'.")

    @app.command("flows-self-check")
    def flows_self_check(
        workspace: Path = typer.Argument(Path("workspace/")),
        domain: str = typer.Option(None, "--domain", "-d"),
        counts_only: bool = typer.Option(
            False,
            "--counts-only",
            help="Print only finding counts, not the findings themselves — "
            "use to check whether anything needs attention without risking "
            "a large payload (e.g. from a caller like tech-lead that must "
            "stay light on context).",
        ),
    ):
        if counts_only:
            print_yaml(get_flows_self_check_summary(workspace, domain))
        else:
            print_yaml(get_flows_self_check(workspace, domain))

    @app.command("self-check")
    def self_check(workspace: Path = typer.Argument(Path("workspace/"))):
        print_yaml(_build_self_check_report(workspace))
