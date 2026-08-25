"""
TUI 检测看板 — 使用 rich 库实时显示刷跑进度 + 检测结果。

用法:
  budaolepao dashboard           # 启动检测看板（等待刷跑数据）
  budaolepao dashboard --demo    # 启动演示模式
"""

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path
from threading import Thread, Event
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich import box
from rich.bar import Bar
from rich.progress import Progress, BarColumn, TextColumn

from integrated.detector import UnifiedDetector
from server.models import GPSPoint

console = Console()


# 配色方案 — 暗色主题，去掉蓝色
C = {
    "bg": "black",
    "fg": "white",
    "accent": "bright_green",
    "warn": "bright_yellow",
    "alert": "bright_red",
    "info": "bright_cyan",
    "dim": "bright_black",
    "header_bg": "bright_black",
}


class DetectionDashboard:
    def __init__(self, demo: bool = False):
        self.detector = UnifiedDetector()
        self.demo = demo
        self._stop = Event()
        self._results = []
        self._run_status = {"running": False}
        self._session_id = f"run_{int(time.time())}"
        self._status_path = Path(__file__).parent.parent / "poc" / "emulator_run" / "run_status.json"

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
            Layout(name="run_progress", size=8),
            Layout(name="trace_table"),
        )
        layout["right"].split_column(
            Layout(name="proactive", ratio=1),
            Layout(name="summary", ratio=1),
        )
        return layout

    def read_run_status(self):
        try:
            if self._status_path.exists():
                data = json.loads(self._status_path.read_text(encoding="utf-8"))
                self._run_status = data
        except Exception:
            pass

    def render_header(self) -> Panel:
        text = Text()
        text.append(" Budao Lepao ", style=f"bold {C['accent']}")
        text.append("| 刷跑 + 检测", style=f"dim {C['info']}")
        text.append(f" | {self._session_id[:8]}", style=f"dim {C['fg']}")
        return Panel(text, style=f"bold white on {C['header_bg']}")

    def render_footer(self, status: str) -> Panel:
        text = Text()
        text.append(f" {status} ", style=f"bold {C['accent']}")
        text.append(f"| 窗口: {len(self._results)} ", style=f"dim")
        if self._run_status.get("running"):
            text.append(f"| 距离: {self._run_status.get('total_dist', 0):.0f}m ", style=C['info'])
        text.append(f"| Ctrl+C 退出", style="dim")
        return Panel(text, style=f"bold white on {C['header_bg']}")

    def render_run_progress(self) -> Panel:
        status = self._run_status
        if not status.get("running") and not self.demo:
            return Panel(
                Text("等待刷跑启动...\n运行 budaolepao run 开始刷跑", style=f"dim {C['fg']}"),
                title="Run Progress",
                style=C['bg'],
            )

        table = Table(box=box.ROUNDED, title="[bold]Run Progress[/bold]")
        table.add_column("Metric", style=C['info'])
        table.add_column("Value", style=C['accent'])

        elapsed = status.get("elapsed", 0)
        speed = status.get("speed", 0)
        dist = status.get("total_dist", 0)
        step_hz = status.get("step_hz", 0)
        frame = status.get("frame", 0)
        steps = status.get("step_count", 0)
        noise = status.get("noise", "")

        table.add_row("Time", f"{elapsed:.1f}s")
        table.add_row("Speed", f"{speed:.2f} m/s")
        table.add_row("Distance", f"{dist:.1f} m")
        table.add_row("Step Rate", f"{step_hz:.2f} Hz")
        table.add_row("Frames", str(frame))
        table.add_row("Steps", str(steps))
        if noise:
            table.add_row("Noise", noise)

        # 进度条
        done = status.get("done", False)
        if done:
            table.add_row("Status", "[bold green]DONE[/bold green]")

        return Panel(table, style=C['bg'])

    def render_trace_table(self) -> Panel:
        table = Table(box=box.ROUNDED, title="[bold]Trace Detection[/bold]")
        table.add_column("Win", style=C['info'])
        table.add_column("Risk", style=C['warn'])
        table.add_column("Verdict", style=C['fg'])
        table.add_column("Trend", style=C['accent'])

        if not self._results:
            table.add_row("-", "-", "-", "-")
        else:
            for r in self._results[-8:]:
                w = r.get("window", 0)
                risk = r.get("window_risk", 0)
                trend = r.get("trend", "stable")
                level = r.get("progressive_level", {}).get("level", "normal")

                risk_str = f"{risk:.2f}"
                if risk > 0.6:
                    risk_str = f"[{C['alert']}]{risk:.2f}[/{C['alert']}]"
                elif risk > 0.3:
                    risk_str = f"[{C['warn']}]{risk:.2f}[/{C['warn']}]"
                else:
                    risk_str = f"[{C['accent']}]{risk:.2f}[/{C['accent']}]"

                v = "NORMAL"
                if risk > 0.6:
                    v = f"[{C['alert']}]ALERT[/{C['alert']}]"
                elif risk > 0.3:
                    v = f"[{C['warn']}]WARN[/{C['warn']}]"

                table.add_row(str(w), risk_str, v, level)

        return Panel(table, style=C['bg'])

    def render_proactive(self) -> Panel:
        table = Table(box=box.SIMPLE, title="[bold]Proactive Check[/bold]")
        table.add_column("Check", style=C['info'])
        table.add_column("Score", style=C['warn'])

        checks = [
            ("TLS", 0.15),
            ("TCP Stack", 0.08),
            ("Timing", 0.12),
            ("Challenge", 0.05),
        ]
        for name, score in checks:
            s = f"[{C['accent']}]{score:.2f}[/{C['accent']}]"
            if score > 0.3:
                s = f"[{C['warn']}]{score:.2f}[/{C['warn']}]"
            table.add_row(name, s)

        return Panel(table, style=C['bg'])

    def render_summary(self) -> Panel:
        table = Table(box=box.SIMPLE, title="[bold]Summary[/bold]")
        table.add_column("Metric", style=C['info'])
        table.add_column("Value", style=C['accent'])

        if not self._results:
            table.add_row("Windows", "0")
            table.add_row("Avg Risk", "0.00")
            table.add_row("Peak Risk", "0.00")
            table.add_row("Warnings", "0")
        else:
            scores = [r.get("window_risk", 0) for r in self._results if r]
            warnings = sum(1 for r in self._results if r and r.get("warning"))
            table.add_row("Windows", str(len(self._results)))
            table.add_row("Avg Risk", f"{sum(scores)/len(scores):.2f}" if scores else "0.00")
            table.add_row("Peak Risk", f"{max(scores):.2f}" if scores else "0.00")
            table.add_row("Warnings", str(warnings))

        d = self._run_status.get("total_dist", 0)
        s = self._run_status.get("speed", 0)
        if d:
            table.add_row("Distance", f"{d:.0f}m")
        if s:
            table.add_row("Speed", f"{s:.2f}m/s")

        return Panel(table, style=C['bg'])

    def generate_demo_point(self, i: int) -> GPSPoint:
        import math
        lon = 114.407 + 0.001 * math.sin(i * 0.1)
        lat = 30.469 + 0.001 * math.cos(i * 0.1)
        return GPSPoint(
            lon=lon, lat=lat,
            accuracy=5.0 + 3.0 * math.sin(i * 0.05),
            timestamp=time.time(),
        )

    def run_demo(self):
        self._run_status = {"running": True}
        det = self.detector.start_session(self._session_id)
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
                "noise": f"(+{0.3*math.sin(i*0.2):+.2f}, {0.3*math.cos(i*0.2):+.2f})",
                "running": True,
            })
            i += 1
            time.sleep(0.5)
        self._run_status["running"] = False

    def run(self):
        layout = self.make_layout()

        if self.demo:
            t = Thread(target=self.run_demo, daemon=True)
            t.start()

        try:
            with Live(layout, refresh_per_second=4, screen=True) as live:
                while not self._stop.is_set():
                    if not self.demo:
                        self.read_run_status()

                    layout["header"].update(self.render_header())
                    layout["run_progress"].update(self.render_run_progress())
                    layout["trace_table"].update(self.render_trace_table())
                    layout["proactive"].update(self.render_proactive())
                    layout["summary"].update(self.render_summary())
                    layout["footer"].update(self.render_footer(
                        "running" if self._run_status.get("running") or self.demo
                        else "waiting..."
                    ))
                    time.sleep(0.25)
        except KeyboardInterrupt:
            self._stop.set()
            console.print(f"\n[{C['accent']}]Dashboard stopped[/{C['accent']}]")


def main():
    parser = argparse.ArgumentParser(description="Detection Dashboard")
    parser.add_argument("--demo", action="store_true", help="Demo mode")
    args = parser.parse_args()

    dashboard = DetectionDashboard(demo=args.demo)
    dashboard.run()


if __name__ == "__main__":
    main()