"""
TUI 检测看板 — 块状进度条、直角边框、灰色斜体标题。
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
from rich.box import SQUARE

from integrated.detector import UnifiedDetector
from server.models import GPSPoint

# ---- 改动 1: 显式锁死终端宽度，避免主屏/alt屏探测到不同宽度导致布局抖动 ----
console = Console(width=120)
spinner = cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")


def risk_color(score: float) -> str:
    if score < 0.3:
        return "green3"
    elif score < 0.6:
        return "yellow3"
    return "red3"


def block_bar(value: float, width: int = 10) -> Text:
    filled = round(value * width)
    filled = max(0, min(width, filled))
    color = risk_color(value)
    bar = Text(overflow="crop", no_wrap=True)
    bar.append("▓" * filled, style=color)
    bar.append("░" * (width - filled), style="grey35")
    return bar


def make_layout() -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )
    layout["body"].split_row(Layout(name="left"), Layout(name="right"))
    layout["left"].split_column(Layout(name="progress"), Layout(name="trace"))
    layout["right"].split_column(Layout(name="check"), Layout(name="summary"))
    return layout


def render_header(run_id: str) -> Panel:
    text = Text()
    text.append(" Budao Lepao", style="bold white")
    text.append("  |  ", style="grey35")
    text.append("刷跑 + 检测", style="grey58")
    text.append("  |  ", style="grey35")
    text.append(run_id, style="bold cyan")
    return Panel(text, box=SQUARE, border_style="grey35", height=3)


def render_progress(data: dict) -> Panel:
    # ---- 改动 2: expand=False，不让表格随父容器宽度抖动而重新拉伸 ----
    table = Table(box=None, show_header=False, padding=(0, 1, 0, 0), expand=False)
    table.add_column(style="grey58", width=12)
    table.add_column(style="white", justify="left")
    for k, v in data.items():
        table.add_row(k, str(v))
    return Panel(
        table,
        title="[grey58 italic]Run Progress[/]",
        title_align="left",
        box=SQUARE,
        border_style="grey35",
    )


def render_check(scores: dict) -> Panel:
    # ---- 改动 3: expand=False + 显式列宽总和，杜绝进度条列被重新分配空间 ----
    table = Table(
        box=None, expand=False, padding=(0, 1, 1, 0),
        show_header=True,
    )
    table.add_column("Check", style="grey58", header_style="bold white", width=14, no_wrap=True)
    table.add_column("Score", justify="right", width=6, header_style="bold white italic", no_wrap=True)
    table.add_column("", width=12, no_wrap=True, overflow="crop")

    for name, score in scores.items():
        color = risk_color(score)
        table.add_row(name, Text(f"{score:.2f}", style=color), block_bar(score))

    return Panel(
        table,
        title="[grey58 italic]Proactive Check[/]",
        title_align="left",
        box=SQUARE,
        border_style="grey35",
    )


def render_trace(windows: list) -> Panel:
    table = Table(box=None, expand=False, padding=(0, 2, 0, 0))
    table.add_column("Win", style="white", width=5)
    table.add_column("Risk", width=6)
    table.add_column("Verdict", width=10)
    table.add_column("Trend", width=10)

    if not windows:
        table.add_row(
            Text("暂无数据,等待首个窗口...", style="grey35 italic"), "", "", ""
        )
    else:
        for w in windows:
            color = risk_color(w["risk"])
            trend_style = "green3" if w["trend"] == "stable" else "yellow3"
            table.add_row(
                Text(str(w["win"]), style="bold white"),
                Text(f'{w["risk"]:.2f}', style=color),
                Text(w["verdict"], style="white"),
                Text(w["trend"], style=f"bold {trend_style}"),
            )
    return Panel(
        table,
        title="[grey58 italic]Trace Detection[/]",
        title_align="left",
        box=SQUARE,
        border_style="grey35",
    )


def render_summary(data: dict) -> Panel:
    table = Table(box=None, show_header=False, padding=(0, 1, 0, 0), expand=False)
    table.add_column(style="grey58", width=12)
    table.add_column(style="white", justify="left")
    for k, v in data.items():
        table.add_row(k, str(v))
    return Panel(
        table,
        title="[grey58 italic]Summary[/]",
        title_align="left",
        box=SQUARE,
        border_style="grey35",
    )


def render_footer(state: str, window: int, total: str = "--") -> Panel:
    frame = next(spinner)
    color = "green3" if state == "running" else "yellow3"
    text = Text()
    text.append(f" {frame} {state}", style=f"bold {color}")
    text.append(f"  |  窗口: {window}/{total}  |  Ctrl+C 退出", style="grey58")
    return Panel(text, box=SQUARE, border_style="grey35", height=3)


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
            lon=lon, lat=lat,
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

        console.clear()
        with Live(
            layout,
            console=console,
            refresh_per_second=6,
            screen=True,
            auto_refresh=True,
        ):
            while not self._stop.is_set():
                if not self.demo:
                    self.read_run_status()

                running = self._run_status.get("running") or self.demo
                s = self._run_status
                progress_data = {}
                if s.get("running") or self.demo:
                    progress_data = {
                        "Time": f"{s.get('elapsed', 0):.1f}s",
                        "Speed": f"{s.get('speed', 0):.2f} m/s",
                        "Distance": f"{s.get('total_dist', 0):.1f} m",
                        "Step Rate": f"{s.get('step_hz', 0):.2f} Hz",
                        "Frames": str(s.get("frame", 0)),
                        "Steps": str(s.get("step_count", 0)),
                    }
                    if s.get("noise"):
                        progress_data["Noise"] = s["noise"]
                    if s.get("done"):
                        progress_data["Status"] = "DONE"
                else:
                    progress_data = {"Status": "等待刷跑启动..."}

                windows = []
                for r in self._results:
                    if r:
                        windows.append({
                            "win": r.get("window", 0),
                            "risk": r.get("window_risk", 0),
                            "verdict": "ALERT" if r.get("window_risk", 0) > 0.6
                                       else "WARN" if r.get("window_risk", 0) > 0.3
                                       else "NORMAL",
                            "trend": r.get("trend", "stable"),
                        })

                ws = [r.get("window_risk", 0) for r in self._results if r]
                summary_data = {
                    "Windows": str(len(self._results)),
                    "Avg Risk": f"{sum(ws)/len(ws):.2f}" if ws else "0.00",
                    "Peak Risk": f"{max(ws):.2f}" if ws else "0.00",
                    "Warnings": str(sum(1 for r in self._results if r and r.get("warning"))),
                }
                if s.get("total_dist", 0):
                    summary_data["Distance"] = f"{s['total_dist']:.0f}m"
                if s.get("speed", 0):
                    summary_data["Speed"] = f"{s['speed']:.2f}m/s"

                layout["header"].update(render_header(self._session_id))
                layout["progress"].update(render_progress(progress_data))
                layout["trace"].update(render_trace(windows))
                layout["check"].update(render_check(scores))
                layout["summary"].update(render_summary(summary_data))
                layout["footer"].update(render_footer(
                    "running" if running else "waiting...",
                    len(self._results),
                ))
                time.sleep(0.15)

        console.clear()


def main():
    parser = argparse.ArgumentParser(description="Detection Dashboard")
    parser.add_argument("--demo", action="store_true", help="Demo mode")
    args = parser.parse_args()

    DetectionDashboard(demo=args.demo).run()


if __name__ == "__main__":
    main()