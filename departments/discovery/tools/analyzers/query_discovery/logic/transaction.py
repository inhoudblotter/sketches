import difflib
import subprocess
import typer
from pathlib import Path
from typing import Dict, List, Tuple


class TransactionManager:
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.backups: Dict[Path, str] = {}
        self.modifications: List[Tuple[Path, str]] = []

    def add_modification(self, file_path: Path, new_content: str):
        """Add a planned modification to the transaction."""
        self.modifications.append((file_path, new_content))

    def _backup(self):
        """Backup original contents of files that are about to be modified."""
        for file_path, _ in self.modifications:
            if file_path.exists() and file_path not in self.backups:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.backups[file_path] = f.read()

    def _write_modifications(self):
        """Write the new content to the files."""
        for file_path, new_content in self.modifications:
            # Ensure parent directories exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

    def _rollback(self):
        """Restore files to their original state."""
        typer.echo(typer.style("Initiating rollback...", fg=typer.colors.RED))
        for file_path, original_content in self.backups.items():
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(original_content)
        # For newly created files (that didn't exist before), we should delete them
        for file_path, _ in self.modifications:
            if file_path not in self.backups and file_path.exists():
                file_path.unlink()
        typer.echo(typer.style("Rollback complete.", fg=typer.colors.YELLOW))

    def _validate(self) -> bool:
        """Run the global workspace validator."""
        typer.echo("Running validation (workspace)...")
        # Use the installed console-script entry point registered in the
        # root pyproject.toml under [project.scripts] as "workspace"
        # (departments.dispatcher:workspace), which dispatches to
        # validators.general.workspace.command. "validate-workspace" is not
        # a registered script and always failed with "No such file or
        # directory".
        cmd = ["workspace", str(self.workspace_dir)]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                typer.echo(typer.style("Validation passed.", fg=typer.colors.GREEN))
                return True
            typer.echo(typer.style("Validation failed!", fg=typer.colors.RED))
            typer.echo(result.stdout)
            typer.echo(result.stderr)
            return False
        except Exception as e:
            typer.echo(
                typer.style(f"Error running validation: {e}", fg=typer.colors.RED)
            )
            return False

    def _render_diff(self, file_path: Path, new_content: str) -> str:
        """Build a human-readable unified diff for a single planned modification."""
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                old_content = f.read()
        else:
            old_content = ""

        diff_lines = list(
            difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}",
            )
        )
        if not diff_lines:
            return f"--- {file_path} (no textual changes)"
        return "".join(diff_lines)

    def execute(self, apply: bool = False):
        """Execute the transaction. If apply is False, just do a dry run."""
        if not self.modifications:
            typer.echo("No changes to apply.")
            return

        if not apply:
            typer.echo(
                typer.style(
                    f"[DRY RUN] Would modify {len(self.modifications)} files:",
                    fg=typer.colors.CYAN,
                )
            )
            for file_path, new_content in self.modifications:
                typer.echo(f" - {file_path}")
                diff_text = self._render_diff(file_path, new_content)
                for line in diff_text.splitlines():
                    if line.startswith("+") and not line.startswith("+++"):
                        typer.echo(typer.style(line, fg=typer.colors.GREEN))
                    elif line.startswith("-") and not line.startswith("---"):
                        typer.echo(typer.style(line, fg=typer.colors.RED))
                    else:
                        typer.echo(line)
            return

        # Execution phase
        try:
            self._backup()
            self._write_modifications()

            if self._validate():
                typer.echo(
                    typer.style(
                        f"Successfully applied {len(self.modifications)} modifications.",
                        fg=typer.colors.GREEN,
                    )
                )
            else:
                self._rollback()
        except Exception as e:
            typer.echo(
                typer.style(f"Exception during transaction: {e}", fg=typer.colors.RED)
            )
            self._rollback()
