import re
import sys
import socketserver
from http.server import BaseHTTPRequestHandler
from pathlib import Path

import typer
import jinja2

from . import logic
from .engine.core.spinner import Spinner, STAGE_LABELS

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _get_env() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=jinja2.select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["regex_replace"] = lambda s, pattern, repl: re.sub(pattern, repl, s)
    return env


def _render(data, serve_mode: bool, fmt: str = "html") -> str:
    env = _get_env()
    if fmt == "workflow":
        template = env.get_template("workflow.md.j2")
        return template.render(report=data)
    if fmt == "md":
        template = env.get_template("report.md.j2")
        return template.render(report=data)
    if fmt == "artifacts":
        template = env.get_template("artifacts.md.j2")
        return template.render(report=data)
    if fmt == "errors":
        template = env.get_template("errors.md.j2")
        return template.render(report=data)
    if fmt == "tools":
        template = env.get_template("tools.md.j2")
        return template.render(report=data)
    template = env.get_template("report.html.j2")
    return template.render(
        report=data,
        report_json=data.model_dump_json(),
        serve_mode=serve_mode,
    )


def pipeline_analysis_cmd(
    department: str = typer.Argument(..., help="Название отдела (например, discovery)"),
    serve: bool = typer.Option(
        False, "--serve", help="Запустить HTTP-сервер с Refresh"
    ),
    port: int = typer.Option(
        7331, "--port", help="Порт HTTP-сервера (только в --serve режиме)"
    ),
) -> None:
    """Генерирует отчёты о состоянии агентов отдела. В --serve режиме запускает HTTP-сервер с кнопкой Refresh."""

    agents_dir = Path(f"departments/{department}/staff")
    workspace_dir = Path(f"workspace/{department}")
    out_dir = Path(f"departments/{department}")

    if serve:

        class _RefreshHandler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args) -> None:  # noqa: A002
                print(format % args, file=sys.stderr)

            def do_GET(self) -> None:
                try:
                    if self.path == "/refresh":
                        data = logic.run(agents_dir, workspace_dir)
                        body = data.model_dump_json().encode("utf-8")
                        self.send_response(200)
                        self.send_header(
                            "Content-Type", "application/json; charset=utf-8"
                        )
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                    else:
                        data = logic.run(agents_dir, workspace_dir)
                        html = _render(data, serve_mode=True)
                        body = html.encode("utf-8")
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                except Exception as exc:
                    print(f"[ERROR] Handler: {exc}", file=sys.stderr)
                    self.send_response(500)
                    self.end_headers()

        print(f"Serving at http://localhost:{port}", file=sys.stderr)
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", port), _RefreshHandler) as httpd:
            httpd.serve_forever()
        return

    # Static file generation mode
    loader = Spinner(stages=list(STAGE_LABELS.keys()))
    loader.start()
    try:
        try:
            data = logic.run(agents_dir, workspace_dir, on_stage=loader.set_stage)
        except Exception as exc:
            loader.stop(success=False)
            typer.echo(f"[ERROR] logic.run failed: {exc}", err=True)
            raise typer.Exit(1) from exc

        try:
            loader.set_stage("render_reports")
            out_dir.mkdir(parents=True, exist_ok=True)

            # HTML Report
            html = _render(data, serve_mode=False, fmt="html")
            (out_dir / "DASHBOARD.html").write_text(html, encoding="utf-8")

            # Markdown Analytics
            md = _render(data, serve_mode=False, fmt="md")
            (out_dir / "ANALYTICS.md").write_text(md, encoding="utf-8")

            # Workflow
            workflow = _render(data, serve_mode=False, fmt="workflow")
            (out_dir / "WORKFLOW.md").write_text(workflow, encoding="utf-8")

            # Artifacts Map
            artifacts = _render(data, serve_mode=False, fmt="artifacts")
            (out_dir / "ARTIFACTS.md").write_text(artifacts, encoding="utf-8")

            # Errors & Warnings
            errors = _render(data, serve_mode=False, fmt="errors")
            (out_dir / "ERRORS.md").write_text(errors, encoding="utf-8")

            # Tools Analytics
            tools_md = _render(data, serve_mode=False, fmt="tools")
            (out_dir / "TOOLS.md").write_text(tools_md, encoding="utf-8")

        except Exception as exc:
            loader.stop(success=False)
            typer.echo(f"[ERROR] Template render/write failed: {exc}", err=True)
            raise typer.Exit(1) from exc

        loader.stop(success=True)
    except typer.Exit:
        raise

    typer.echo("")
    raise typer.Exit(0)


command = pipeline_analysis_cmd

if __name__ == "__main__":
    typer.run(pipeline_analysis_cmd)
