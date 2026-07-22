from __future__ import annotations

import math
import threading
import time

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

ART = [
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ ",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡄⠀⠀⠀⡇⠀⢀⠞⠹⣆⠀⢠⠀⠀⠀⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ ",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠠⡀⠀⠀⠘⡄⠀⠀⢸⣠⠎⣰⣧⠘⣄⡼⠀⠀⢀⡞⠀⠀⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ ",
    "⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⠀⠀⠑⣄⠀⠀⢹⡄⢠⣸⠋⣴⣿⢿⣷⡘⢇⡠⢀⡞⠀⠀⢀⠜⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ ",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠈⠲⣄⠀⠀⠘⢧⡀⣆⢿⣼⠃⣼⡿⠁⠀⢻⣷⡈⢧⣾⣡⠂⣴⠏⠀⠀⢀⠔⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀ ",
    "⠀⠀⠀⠀⠀⠀⠤⡀⠀⠀⠈⠳⣦⡑⣬⣿⣾⡿⢁⣾⡿⠁⠀⠀⠀⠻⣿⡄⢻⣿⣾⣣⠖⣠⠞⠁⠀⠀⠀⡀⠀⠀⠀⠀⠀⠀⠀ ",
    "⠀⠀⠀⠀⠀⠀⠀⠈⠓⢦⣄⡐⢬⣻⣾⣿⡿⢡⣾⡟⠀⠀⠀⠀⠀⠀⠹⣿⣆⢻⣿⣿⣿⣡⠖⣀⡤⠖⠉⠀⠀⠀⠀⠀⠀⠀⠀ ",
    "⠀⠀⠀⠀⠀⠤⣀⣀⠀⠀⢬⣛⣿⣿⣿⡟⢠⣿⠏⠀⠀⠀⠀⠀⠀⠀⠀⠙⣿⣆⠹⣿⣿⣿⣟⡭⠄⠀⢀⣀⠠⠀⠀⠀⠀⠀⠀ ",
    "⠀⠀⠀⠀⠀⠀⠀⠈⠙⠓⠶⣾⣿⣿⠟⣠⣿⠋⣠⣴⣶⠿⠿⠻⠿⢷⣦⣄⡘⢿⣦⠙⣿⣿⣿⡶⠞⠋⠉⠀⠀⠀⠀⠀⠀⠀⠀ ",
    "⠀⠀⠀⠀⠀⠠⠤⠤⣤⣭⣿⣿⣿⠋⣰⣿⣿⣿⣿⣯⡶⢶⣶⣶⣶⢶⣮⣿⣿⣾⣿⣧⡘⣿⣿⣿⣭⣤⡤⠤⠄⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠤⠼⣿⠃⣼⣿⣿⡟⠉⠁⠸⣧⠸⣿⣿⡿⢠⡿⠀⠉⢛⣿⣿⣷⡈⢿⡿⠤⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ ",
    "⠀⠀⠀⠀⠀⠀⠐⠒⠚⢛⡿⢃⣼⡿⠉⠙⢿⣷⣤⣀⠙⢷⣬⣥⡴⠟⢁⣠⣴⡿⠟⠁⠻⣷⡈⢻⣛⠛⠒⠒⠂⠀⠀⠀⠀⠀⠀ ",
    "⠀⠀⠀⠀⠀⠀⠀⠀⣀⡼⢁⣾⡟⠀⠀⠀⠀⠈⠛⠿⢿⣶⣶⣶⣾⣿⠿⠛⠉⠀⠀⠀⠀⠹⣿⡄⢻⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀ ",
    "⠀⠀⠀⠀⠀⠐⠊⢉⡝⢠⣾⠟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣿⣆⠹⡉⠉⠒⠀⠀⠀⠀⠀⠀ ",
    "⠀⠀⠀⠀⠀⠀⢀⡞⠠⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⢦⠹⣄⠀⠀⠀⠀⠀⠀⠀ ",
    "⠀⠀⠀⠀⠀⠀⠛⠒⠒⠒⠒⣶⠖⢲⠖⣶⢶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⡖⢶⠲⢶⡒⠒⠒⠒⠛⠂⠀⠀⠀⠀⠀⠀ ",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⡤⠊⠀⠀⢀⡾⠁⠞⣽⢋⡿⣿⢿⢿⣿⣿⣿⡹⡏⢿⡙⡌⠻⣄⠀⠀⠉⠢⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀ ",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠋⠀⠀⢰⠇⠘⢠⡏⠸⠘⡇⠹⠸⡇⠑⠈⢧⠀⠀⠘⢆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ ",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠐⠁⠀⠀⢠⠏⠀⠀⣸⠁⠀⠀⡇⠀⠀⢻⠀⠀⠈⢆⠀⠀⠀⠓⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ ",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠋⠀⠀⠀⡏⠀⠀⠀⡇⠀⠀⠘⡄⠀⠀⠈⠆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ ",
    "                            ⠁⠀⠀⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀  ",
]

STAGE_LABELS: dict[str, str] = {
    "parse_agents": "PARSING AGENT MANIFESTS",
    "parse_tools": "INDEXING TOOL REGISTRY",
    "build_graph": "ASSEMBLING DEPENDENCY GRAPH",
    "check_status": "POLLING AGENT STATUS",
    "compute_metrics": "COMPUTING METRICS",
    "run_tests": "RUNNING TOOL TEST SUITE",
    "check_contract_drift": "SCANNING CONTRACT DRIFT",
    "check_git_coverage": "AUDITING GIT COVERAGE",
    "measure_costs": "MEASURING CONTEXT COSTS",
    "build_playbooks": "MAPPING PLAYBOOK REFERENCES",
    "build_legacy": "DETECTING DEAD ASSETS",
    "build_stages": "RESOLVING EXECUTION STAGES",
    "build_artifacts": "TRACING ARTIFACT LINEAGE",
    "render_reports": "RENDERING REPORTS",
}

STAGE_ORDER = list(STAGE_LABELS.keys())

_ART_WIDTH = max(len(line) for line in ART)
_STAGE_COL_WIDTH = max(len(label) for label in STAGE_LABELS.values()) + 3


class Spinner:
    def __init__(
        self, stages: list[str] | None = None, refresh_per_second: float = 20.0
    ):
        self.stages = stages or STAGE_ORDER
        self.current: str | None = None
        self.completed: list[str] = []
        self.failed = False
        self._start_time = 0.0
        self._console = Console(stderr=True)
        self._live: Live | None = None
        self._frame = 0
        self._refresh_per_second = refresh_per_second
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def set_stage(self, key: str) -> None:
        with self._lock:
            if self.current and self.current not in self.completed:
                self.completed.append(self.current)
            self.current = key

    def start(self) -> None:
        self._start_time = time.time()
        if not self._console.is_terminal:
            self._console.print("[dim]pipeline analysis started[/dim]")
            return
        self._live = Live(
            self._render(),
            console=self._console,
            refresh_per_second=self._refresh_per_second,
            transient=False,
        )
        self._live.start()
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()

    def _animate(self) -> None:
        while not self._stop_event.wait(1.0 / self._refresh_per_second):
            self._frame += 1
            if self._live:
                self._live.update(self._render())

    def stop(self, success: bool = True) -> None:
        with self._lock:
            if self.current and self.current not in self.completed:
                self.completed.append(self.current)
            self.current = None
            self.failed = not success
        if not self._live:
            elapsed = time.time() - self._start_time
            status = "OK" if success else "FAILED"
            self._console.print(
                f"[dim]pipeline analysis finished ({status}) in {elapsed:.1f}s[/dim]"
            )
            return
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        self._live.update(self._render(final=True))
        self._live.stop()

    def _render(self, final: bool = False) -> Panel:
        with self._lock:
            completed = list(self.completed)
            current = self.current
            failed = self.failed

        elapsed = time.time() - self._start_time

        if final:
            glow = "green" if not failed else "red"
        else:
            progress = (math.cos(elapsed * math.pi) + 1) / 2
            r = int(255 * progress)
            g = int(255 * (1 - progress))
            b = 255
            glow = f"#{r:02x}{g:02x}{b:02x}"

        pyramid_text = Text("\n".join(ART), style=f"bold {glow}")

        stage_lines = Text()
        spinner = "◐◓◑◒"[int(elapsed * 6) % 4]
        for key in self.stages:
            label = STAGE_LABELS.get(key, key)
            if key in completed:
                stage_lines.append(" ✓ ", style="bold green")
                stage_lines.append(label + "\n", style="dim")
            elif key == current:
                stage_lines.append(f" {spinner} ", style=f"bold {glow}")
                stage_lines.append(label + "\n", style=f"bold {glow}")
            else:
                stage_lines.append("   ", style="grey42")
                stage_lines.append(label + "\n", style="grey42")

        if final:
            status = "ANOMALY DETECTED" if failed else "ALL SYSTEMS NOMINAL"
            footer = Text(f"{status}  ·  {elapsed:.1f}s", style=f"bold {glow}")
        else:
            footer = Text(f"elapsed {elapsed:.1f}s", style="grey42")

        stage_panel = Group(stage_lines, Text(""), footer)

        # Fixed 2-column grid, pyramid | stages — same column widths every
        # frame, so nothing reflows besides color and the stage/footer text.
        grid = Table.grid(padding=(0, 3))
        grid.add_column(width=_ART_WIDTH, no_wrap=True)
        grid.add_column(width=_STAGE_COL_WIDTH, no_wrap=True)
        grid.add_row(pyramid_text, stage_panel)

        return Panel(
            grid,
            border_style=glow,
            padding=(1, 2),
            expand=False,
        )
