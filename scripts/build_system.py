import sys
import yaml
import importlib
from pathlib import Path
import re


def build_aliases():
    root_dir = Path(__file__).resolve().parent.parent
    departments_dir = root_dir / "departments"

    tools = []

    for meta_path in departments_dir.rglob("meta.yaml"):
        tool_dir = meta_path.parent
        if "__pycache__" in tool_dir.parts or "__tests__" in tool_dir.parts:
            continue

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}

        module_dotted = ".".join(tool_dir.relative_to(root_dir).parts + ("command",))
        cli_name = meta.get("cli_name", tool_dir.name.replace("_", "-"))

        aliases = [cli_name] + meta.get("cli_aliases", [])

        for alias in aliases:
            func_name = alias.replace("-", "_")
            tools.append(
                {
                    "cli_name": alias,
                    "func_name": func_name,
                    "module_dotted": module_dotted,
                }
            )

    tools.sort(key=lambda x: x["cli_name"])

    dispatcher_path = departments_dir / "dispatcher.py"
    with open(dispatcher_path, "w", encoding="utf-8") as f:
        f.write('"""Auto-generated script to dispatch CLI commands."""\n')
        f.write("import importlib\n")
        f.write("import typer\n\n")
        f.write("def run_command(module_dotted: str):\n")
        f.write("    try:\n")
        f.write("        module = importlib.import_module(module_dotted)\n")
        f.write('        cmd = getattr(module, "command", None)\n')
        f.write("        if cmd is None:\n")
        f.write(
            '            typer.secho(f"Warning: {module_dotted} does not expose a `command` attribute.", fg=typer.colors.YELLOW, err=True)\n'
        )
        f.write("            return\n")
        f.write("        if isinstance(cmd, typer.Typer):\n")
        f.write("            cmd()\n")
        f.write("        else:\n")
        f.write("            typer.run(cmd)\n")
        f.write("    except Exception as e:\n")
        f.write(
            '        typer.secho(f"Error executing {module_dotted}: {e}", fg=typer.colors.RED, err=True)\n'
        )
        f.write("        raise typer.Exit(1) from e\n\n")

        for tool in tools:
            f.write(f'def {tool["func_name"]}():\n')
            f.write(f'    run_command("{tool["module_dotted"]}")\n\n')

    import subprocess

    subprocess.run(["black", "-q", str(dispatcher_path)], check=False)

    pyproject_path = root_dir / "pyproject.toml"
    with open(pyproject_path, "r", encoding="utf-8") as f:
        content = f.read()

    scripts_section = "[project.scripts]\n"
    for tool in tools:
        scripts_section += (
            f'{tool["cli_name"]} = "departments.dispatcher:{tool["func_name"]}"\n'
        )

    content = re.sub(
        r"\[project\.scripts\].*?(?=\n\[|$)", scripts_section, content, flags=re.DOTALL
    )

    with open(pyproject_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(
        f"Generated departments/dispatcher.py and updated pyproject.toml with {len(tools)} aliases."
    )


def main():
    print("Building system aliases...")
    build_aliases()
    print("System build complete.")


if __name__ == "__main__":
    main()
