"""
TUI 检测看板 — 黑白风格，实时显示刷跑进度 + 检测结果。
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path
from threading import Thread, Event
from itertools import cycle

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.progress_bar import ProgressBar

from integrated.detector import UnifiedDetector
from server.models import GPSPoint

console = Console()
spinner_frames = cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")


def risk_color(score: float) -> str:
    if score < 0.3:
        return "green"
    elif score < 0.6:
        return "yellow"
    return "red"


def make_layout() -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )
    layout["body"].split_row(
        Layout(name="left", ratio=3),
        Layout(name="right", ratio=2),
    )
    layout["left"].split_column(
        Layout(name="progress"),
        Layout(name="trace"),
    )
    layout["right"].split_column(
        Layout(name="check"),
        Layout(name="summary"),
    )
    return layout


def render_header(run_id: str) -> Panel:
    text = Text()
    text.append("Budao Lepao", style="bold white")
    text.append("  |  ", style="dim")
    text.append("刷跑 + 检测", style="grey70")
    text.append("  |  ", style="dim")
    text.append(run_id, style="bold cyan")
    return Panel(Align.left(text), border_style="grey35", height=3)


def render_footer(state: str, window: int, total: int | None):
    frame = next(spinner_frames)
    total_str = str(total) if total else "--"
    text = Text()
    text.append(
        f"{frame} {state}",
        style="bold yellow" if state == "waiting..." else "bold green",
    )
    text.append(f"  |  窗口: {window}/{total_str}  |  Ctrl+C 退出", style="dim")
    return Panel(text, border_style="grey35", height=3)


def render_check(scores: dict) -> Panel:
    table = Table(box=None, expand=True, show_header=True, header_style="dim italic")
    table.add_column("Check", style="grey70")
    table.add_column("Score", justify="right")
    table.add_column("", width=12)

    for name, score in scores.items():
        color = risk_color(score)
        bar = ProgressBar(
            total=1.0,
            completed=score,
            width=10,
            complete_style=color,
            finished_style=color,
        )
        table.add_row(name, f"[{color}]{score:.2f}[/]", bar)

    return Panel(
        table,
        title="[italic]Proactive Check[/]",
        title_align="left",
        border_style="grey35",
    )


def render_trace(windows: list) -> Panel:
    table = Table(box=None, expand=True, header_style="dim")
    for col in ["Win", "Risk", "Verdict", "Trend"]:
        table.add_column(col)

    if not windows:
        table.add_row(Text("暂无数据,等待首个窗口...", style="dim italic"), "", "", "")
    else:
        for w in windows:
            risk = w.get("window_risk", 0)
            color = risk_color(risk)
            v = "NORMAL"
            if risk > 0.6:
                v = "ALERT"
            elif risk > 0.3:
                v = "WARN"
            table.add_row(
                str(w.get("window", 0)),
                f"[{color}]{risk:.2f}[/]",
                v,
                w.get("trend", "-"),
            )

    return Panel(
        table,
        title="[italic]Trace Detection[/]",
        title_align="left",
        border_style="grey35",
    )


def render_progress(status: dict) -> Panel:
    table = Table(box=None, expand=True, show_header=False)
    table.add_column(style="grey70")
    table.add_column(style="white")

    if not status.get("running"):
        return Panel(
            Text("等待刷跑启动...\n运行 budaolepao run 开始刷跑", style="dim italic"),
            title="[italic]Run Progress[/]",
            title_align="left",
            border_style="grey35",
        )

    table.add_row("Time", f"{status.get('elapsed', 0):.1f}s")
    table.add_row("Speed", f"{status.get('speed', 0):.2f} m/s")
    table.add_row("Distance", f"{status.get('total_dist', 0):.1f} m")
    table.add_row("Step Rate", f"{status.get('step_hz', 0):.2f} Hz")
    table.add_row("Frames", str(status.get("frame", 0)))
    table.add_row("Steps", str(status.get("step_count", 0)))
    if status.get("noise"):
        table.add_row("Noise", status["noise"])
    if status.get("done"):
        table.add_row("Status", "DONE")

    return Panel(
        table,
        title="[italic]Run Progress[/]",
        title_align="left",
        border_style="grey35",
    )


def render_summary(status: dict, windows: list) -> Panel:
    table = Table(box=None, expand=True, show_header=False)
    table.add_column(style="grey70")
    table.add_column(style="white")

    if windows:
        scores = [r.get("window_risk", 0) for r in windows if r]
        warnings = sum(1 for r in windows if r and r.get("warning"))
        table.add_row("Windows", str(len(windows)))
        table.add_row("Avg Risk", f"{sum(scores)/len(scores):.2f}" if scores else "0.00")
        table.add_row("Peak Risk", f"{max(scores):.2f}" if scores else "0.00")
        table.add_row("Warnings", str(warnings))
    else:
        table.add_row("Windows", "0")
        table.add_row("Avg Risk", "0.00")
        table.add_row("Peak Risk", "0.00")
        table.add_row("Warnings", "0")

    d = status.get("total_dist", 0)
    s = status.get("speed", 0)
    if d:
        table.add_row("Distance", f"{d:.0f}m")
    if s:
        table.add_row("Speed", f"{s:.2f}m/s")

    return Panel(
        table,
        title="[italic]Summary[/]",
        title_align="left",
        border_style="grey35",
    )


class DetectionDashboard:
    def __init__(self, demo: bool = False):
        self.detector = UnifiedDetector()
        self.demo = demo
        self._stop = Event()
        self._results = []
        self._run_status = {"running": False}
        self._session_id = f"run_{int(time.time()) % 10000}"
        self._status_path = (
            Path(__file__).parent.parent
            / "poc"
            / "emulator_run"
            / "run_status.json"
        )

    def read_run_status(self):
        try:
            if self._status_path.exists():
                self._run_status = json.loads(
                    self._status_path.read_text(encoding="utf-8")
                )
        except Exception:
            pass

    def generate_demo_point(self, i: int) -> GPSPoint:
        lon = 114.407 + 0.001 * math.sin(i * 0.1)
        lat = 30.469 + 0.001 * math.cos(i * 0.1)
        return GPSPoint(
            lon=lon,
            lat=lat,
            accuracy=5.0 + 3.0 * math.sin(i * 0.05),
            timestamp=time.time(),
        )

    def run_demo(self):
        self._run_status = {"running": True}
        self.detector.start_session(self._session_id)
        i = 0
        while not self._stop.is_set():
            point = self.generate_demo_point(i)
            result = self.detector.feed(self._session_id, point)
            if result:
                self._results.append(result)
            self._run_status.update({
                "elapsed": i * 0.5,
                "speed": 4.0 + 0.5 * math.sin(i * 0.1),
                "total_dist": i * 2.0,
                "step_hz": 2.0 + 0.3 * math.sin(i * 0.05),
                "frame": i,
                "step_count": i * 3,
                "noise": f"({0.3*math.sin(i*0.2):+.2f}, {0.3*math.cos(i*0.2):+.2f})",
                "running": True,
            })
            i += 1
            time.sleep(0.5)
        self._run_status["running"] = False

    def run(self):
        layout = make_layout()

        if self.demo:
            Thread(target=self.run_demo, daemon=True).start()

        scores = {
            "TLS": 0.15,
            "TCP Stack": 0.08,
            "Timing": 0.12,
            "Challenge": 0.05,
        }
        window_count = 0

        with Live(layout, console=console, refresh_per_second=8, screen=True) as live:
            while not self._stop.is_set():
                if not self.demo:
                    self.read_run_status()

                running = self._run_status.get("running") or self.demo

                layout["header"].update(render_header(self._session_id))
                layout["progress"].update(render_progress(self._run_status))
                layout["trace"].update(render_trace(self._results))
                layout["check"].update(render_check(scores))
                layout["summary"].update(render_summary(self._run_status, self._results))
                layout["footer"].update(
                    render_footer(
                        "running" if running else "waiting...",
                        len(self._results),
                        None,
                    )
                )
                time.sleep(0.12)


def main():
    parser = argparse.ArgumentParser(description="Detection Dashboard")
    parser.add_argument("--demo", action="store_true", help="Demo mode")
    args = parser.parse_args()

    DetectionDashboard(demo=args.demo).run()


if __name__ == "__main__":
    main()