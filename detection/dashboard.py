"""
TUI 检测看板 — 黑白风格，实时显示刷跑进度 + 检测结果。

用法:
  budaolepao dashboard           # 启动检测看板（等待刷跑数据）
  budaolepao dashboard --demo    # 启动演示模式
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path
from threading import Thread, Event

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich import box

from integrated.detector import UnifiedDetector
from server.models import GPSPoint

console = Console()


class DetectionDashboard:
    def __init__(self, demo: bool = False):
        self.detector = UnifiedDetector()
        self.demo = demo
        self._stop = Event()
        self._results = []
        self._run_status = {"running": False}
        self._session_id = f"run_{int(time.time()) % 10000}"
        self._status_path = (
            Path(__file__).parent.parent / "poc" / "emulator_run" / "run_status.json"
        )

    # ----------------------------------------------------------
    # 布局
    # ----------------------------------------------------------
    def make_layout(self) -> Layout:
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
            Layout(name="run_progress", ratio=1),
            Layout(name="trace_table", ratio=2),
        )
        layout["right"].split_column(
            Layout(name="proactive", ratio=1),
            Layout(name="summary", ratio=1),
        )
        return layout

    def read_run_status(self):
        try:
            if self._status_path.exists():
                self._run_status = json.loads(
                    self._status_path.read_text(encoding="utf-8")
                )
        except Exception:
            pass

    # ----------------------------------------------------------
    # 各区块渲染
    # ----------------------------------------------------------
    def render_header(self) -> Panel:
        text = Text()
        text.append(" Budao Lepao ", style="bold white")
        text.append("| 刷跑 + 检测 ", style="dim")
        text.append(f"| {self._session_id}", style="dim")
        return Panel(text, border_style="white", style="black")

    def render_footer(self, status: str) -> Panel:
        text = Text()
        text.append(f" {status} ", style="bold white")
        text.append(f"| 窗口: {len(self._results)} ", style="dim")
        if self._run_status.get("running"):
            text.append(
                f"| 距离: {self._run_status.get('total_dist', 0):.0f}m ",
                style="dim",
            )
        text.append("| Ctrl+C 退出", style="dim")
        return Panel(text, border_style="white", style="black")

    def render_run_progress(self) -> Panel:
        status = self._run_status
        if not status.get("running") and not self.demo:
            return Panel(
                Text("等待刷跑启动...\n运行 budaolepao run 开始刷跑", style="dim"),
                title="Run Progress",
                title_align="left",
                border_style="white",
                style="black",
            )

        table = Table(box=None, show_header=False, padding=(0, 1))
        table.add_column(style="dim")
        table.add_column(style="white")
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
            title="Run Progress",
            title_align="left",
            border_style="white",
            style="black",
        )

    def render_trace_table(self) -> Panel:
        table = Table(
            box=None,
            title="Trace Detection",
            title_style="italic dim",
            header_style="dim",
            padding=(0, 1),
        )
        table.add_column("Win")
        table.add_column("Risk")
        table.add_column("Verdict")
        table.add_column("Trend")

        if not self._results:
            table.add_row("-", "-", "-", "-")
        else:
            for r in self._results[-8:]:
                risk = r.get("window_risk", 0)
                level = r.get("progressive_level", {}).get("level", "normal")
                v = "NORMAL"
                if risk > 0.6:
                    v = "ALERT"
                elif risk > 0.3:
                    v = "WARN"
                table.add_row(
                    str(r.get("window", 0)),
                    f"{risk:.2f}",
                    v,
                    level,
                )

        return Panel(table, border_style="white", style="black")

    def render_proactive(self) -> Table:
        table = Table(
            box=None,
            title="Proactive Check",
            title_style="italic dim",
            header_style="dim",
            padding=(0, 1),
        )
        table.add_column("Check")
        table.add_column("Score")

        checks = [
            ("TLS", 0.15),
            ("TCP Stack", 0.08),
            ("Timing", 0.12),
            ("Challenge", 0.05),
        ]
        for name, score in checks:
            table.add_row(name, f"{score:.2f}")

        return table

    def render_summary(self) -> Panel:
        table = Table(
            box=None,
            title="Summary",
            title_style="italic dim",
            header_style="dim",
            padding=(0, 1),
        )
        table.add_column("Metric")
        table.add_column("Value")

        if self._results:
            scores = [r.get("window_risk", 0) for r in self._results if r]
            warnings = sum(1 for r in self._results if r and r.get("warning"))
            table.add_row("Windows", str(len(self._results)))
            table.add_row("Avg Risk", f"{sum(scores)/len(scores):.2f}")
            table.add_row("Peak Risk", f"{max(scores):.2f}")
            table.add_row("Warnings", str(warnings))
        else:
            table.add_row("Windows", "0")
            table.add_row("Avg Risk", "0.00")
            table.add_row("Peak Risk", "0.00")
            table.add_row("Warnings", "0")

        d = self._run_status.get("total_dist", 0)
        s = self._run_status.get("speed", 0)
        if d:
            table.add_row("Distance", f"{d:.0f}m")
        if s:
            table.add_row("Speed", f"{s:.2f}m/s")

        return Panel(table, border_style="white", style="black")

    # ----------------------------------------------------------
    # 演示数据
    # ----------------------------------------------------------
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

    # ----------------------------------------------------------
    # 主循环
    # ----------------------------------------------------------
    def run(self):
        layout = self.make_layout()

        if self.demo:
            Thread(target=self.run_demo, daemon=True).start()

        try:
            with Live(layout, refresh_per_second=4, screen=True):
                while not self._stop.is_set():
                    if not self.demo:
                        self.read_run_status()

                    running = self._run_status.get("running") or self.demo
                    layout["header"].update(self.render_header())
                    layout["run_progress"].update(self.render_run_progress())
                    layout["trace_table"].update(self.render_trace_table())
                    layout["proactive"].update(self.render_proactive())
                    layout["summary"].update(self.render_summary())
                    layout["footer"].update(
                        self.render_footer("running" if running else "waiting...")
                    )
                    time.sleep(0.25)
        except KeyboardInterrupt:
            self._stop.set()
            console.print("\nDashboard stopped")


def main():
    parser = argparse.ArgumentParser(description="Detection Dashboard")
    parser.add_argument("--demo", action="store_true", help="Demo mode")
    args = parser.parse_args()

    DetectionDashboard(demo=args.demo).run()


if __name__ == "__main__":
    main()
