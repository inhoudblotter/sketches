"""Auto-generated script to dispatch CLI commands."""

import importlib
import typer


def run_command(module_dotted: str):
    try:
        module = importlib.import_module(module_dotted)
        cmd = getattr(module, "command", None)
        if cmd is None:
            typer.secho(
                f"Warning: {module_dotted} does not expose a `command` attribute.",
                fg=typer.colors.YELLOW,
                err=True,
            )
            return
        if isinstance(cmd, typer.Typer):
            cmd()
        else:
            typer.run(cmd)
    except Exception as e:
        typer.secho(
            f"Error executing {module_dotted}: {e}", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(1) from e


def build_project_analytics():
    run_command(
        "departments.discovery.tools.generators.build_project_analytics.command"
    )


def business_observability():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.strategy.business_observability.command"
    )


def discovery_linter():
    run_command("departments.discovery.tools.linters.discovery_linter.command")


def domain():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.domain.domain.command"
    )


def domain_dictionary():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.domain.domain_dictionary.command"
    )


def domain_exports():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.domain.domain_exports.command"
    )


def domain_orphans():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.domain.domain_orphans.command"
    )


def domain_summary():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.domain.domain_summary.command"
    )


def domains_manifest():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.domain.domains_manifest.command"
    )


def economics():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.strategy.economics.command"
    )


def entity_graph():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.tech.entity_graph.command"
    )


def errata():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.epic.errata.command"
    )


def estimation():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.epic.estimation.command"
    )


def extract_bounded_contexts():
    run_command(
        "departments.discovery.tools.preprocessors.extract_bounded_contexts.command"
    )


def features():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.epic.features.command"
    )


def flows_batch():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.epic.flows_batch.command"
    )


def generate_pitch_deck():
    run_command("departments.discovery.tools.generators.generate_pitch_deck.command")


def geopolitics():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.strategy.geopolitics.command"
    )


def job_stories():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.epic.job_stories.command"
    )


def job_stories_content():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.epic.job_stories_content.command"
    )


def launch_roadmap():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.strategy.launch_roadmap.command"
    )


def markdown_headings():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.markdown.markdown_headings.command"
    )


def markdown_links():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.markdown.markdown_links.command"
    )


def market_context():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.strategy.market_context.command"
    )


def patch():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.general.patch.command"
    )


def pipeline_analysis():
    run_command("departments.operations.tools.pipeline_analysis.command")


def pitch_deck():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.strategy.pitch_deck.command"
    )


def platform_coverage():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.strategy.platform_coverage.command"
    )


def platform_strategy():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.strategy.platform_strategy.command"
    )


def query_discovery():
    run_command("departments.discovery.tools.analyzers.query_discovery.command")


def revenue_model():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.strategy.revenue_model.command"
    )


def strategy():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.general.strategy.command"
    )


def stress_test():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.strategy.economics.stress_test.command"
    )


def target_audience():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.strategy.target_audience.command"
    )


def tech_constraints():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.tech.tech_constraints.command"
    )


def tech_market_brief():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.tech.tech_market_brief.command"
    )


def tech_synthesis():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.tech.tech_synthesis.command"
    )


def user_flows():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.general.user_flows.command"
    )


def ux_constraints():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.general.ux_constraints.command"
    )


def validate_agent():
    run_command("departments.operations.tools.validators.validate_agent.command")


def validate_git_coverage():
    run_command("departments.operations.tools.validators.validate_git_coverage.command")


def workspace():
    run_command(
        "departments.discovery.tools.linters.discovery_linter.validators.general.workspace.command"
    )
