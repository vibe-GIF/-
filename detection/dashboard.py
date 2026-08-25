"""
TUI 检测看板 — 使用 rich 库实时显示检测结果。

用法:
  budaolepao dashboard           # 启动检测看板
  budaolepao dashboard --demo    # 启动演示模式（自动生成模拟数据）
"""

import argparse
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

from integrated.detector import UnifiedDetector
from server.models import GPSPoint

console = Console()


class DetectionDashboard:
    def __init__(self, demo: bool = False):
        self.detector = UnifiedDetector()
        self.demo = demo
        self._stop = Event()
        self._results = []
        self._session_id = f"run_{int(time.time())}"

    def make_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )
        layout["body"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1),
        )
        layout["left"].split_column(
            Layout(name="trace_table", ratio=2),
            Layout(name="rule_detail", ratio=1),
        )
        layout["right"].split_column(
            Layout(name="proactive", ratio=1),
            Layout(name="summary", ratio=1),
        )
        return layout

    def render_header(self) -> Panel:
        text = Text()
        text.append(" Budao Lepao Detection Dashboard ", style="bold cyan")
        text.append(f" | Session: {self._session_id[:12]}...", style="dim")
        return Panel(text, style="bold white on blue")

    def render_footer(self, status: str) -> Panel:
        text = Text()
        text.append(f" Status: {status} ", style="bold green")
        text.append(f" | Windows: {len(self._results)} ", style="dim")
        text.append(f" | Press Ctrl+C to stop", style="dim")
        return Panel(text, style="bold white on black")

    def render_trace_table(self) -> Panel:
        table = Table(box=box.ROUNDED, title="Trace Detection")
        table.add_column("Window", style="cyan")
        table.add_column("Risk", style="magenta")
        table.add_column("Verdict", style="yellow")
        table.add_column("Trend", style="green")

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
                    risk_str = f"[red]{risk:.2f}[/red]"
                elif risk > 0.3:
                    risk_str = f"[yellow]{risk:.2f}[/yellow]"
                else:
                    risk_str = f"[green]{risk:.2f}[/green]"

                v = "NORMAL"
                if risk > 0.6:
                    v = "[red]ALERT[/red]"
                elif risk > 0.3:
                    v = "[yellow]WARN[/yellow]"

                table.add_row(str(w), risk_str, v, level)

        return Panel(table, style="bold white on black")

    def render_rule_detail(self) -> Panel:
        table = Table(box=box.SIMPLE, title="Rule Results")
        table.add_column("Rule", style="cyan")
        table.add_column("Result", style="green")

        if not self._results:
            table.add_row("-", "-")
        else:
            latest = self._results[-1]
            rule_results = latest.get("rule_results", {})
            for name, result in list(rule_results.items())[:6]:
                status = "PASS" if result["passed"] else "[red]FAIL[/red]"
                score = result["score"]
                short = name[:20]
                table.add_row(short, f"{status} ({score:.2f})")

        return Panel(table, style="bold white on black")

    def render_proactive(self) -> Panel:
        table = Table(box=box.SIMPLE, title="Proactive Detection")
        table.add_column("Check", style="cyan")
        table.add_column("Score", style="magenta")

        # Simulate proactive results for demo
        proactive = [
            ("TLS Fingerprint", 0.15),
            ("TCP Stack", 0.08),
            ("Timing", 0.12),
            ("Challenge", 0.05),
        ]
        for name, score in proactive:
            score_str = f"[green]{score:.2f}[/green]"
            if score > 0.3:
                score_str = f"[red]{score:.2f}[/red]"
            table.add_row(name, score_str)

        return Panel(table, style="bold white on black")

    def render_summary(self) -> Panel:
        table = Table(box=box.SIMPLE, title="Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")

        if not self._results:
            table.add_row("Windows", "0")
            table.add_row("Avg Risk", "0.00")
            table.add_row("Max Risk", "0.00")
            table.add_row("Warnings", "0")
        else:
            scores = [r.get("window_risk", 0) for r in self._results if r]
            warnings = sum(1 for r in self._results if r and r.get("warning"))
            table.add_row("Windows", str(len(self._results)))
            table.add_row("Avg Risk", f"{sum(scores)/len(scores):.2f}" if scores else "0.00")
            table.add_row("Max Risk", f"{max(scores):.2f}" if scores else "0.00")
            table.add_row("Warnings", str(warnings))

        return Panel(table, style="bold white on black")

    def generate_demo_point(self, i: int) -> GPSPoint:
        base_lon, base_lat = 114.407, 30.469
        import math
        lon = base_lon + 0.001 * math.sin(i * 0.1)
        lat = base_lat + 0.001 * math.cos(i * 0.1)
        return GPSPoint(
            lon=lon, lat=lat,
            accuracy=5.0 + 3.0 * math.sin(i * 0.05),
            timestamp=time.time(),
        )

    def run_demo(self):
        det = self.detector.start_session(self._session_id)
        i = 0
        while not self._stop.is_set():
            point = self.generate_demo_point(i)
            result = self.detector.feed(self._session_id, point)
            if result:
                self._results.append(result)
            i += 1
            time.sleep(0.5)

    def run(self):
        layout = self.make_layout()

        if self.demo:
            t = Thread(target=self.run_demo, daemon=True)
            t.start()

        try:
            with Live(layout, refresh_per_second=4, screen=True) as live:
                while not self._stop.is_set():
                    layout["header"].update(self.render_header())
                    layout["trace_table"].update(self.render_trace_table())
                    layout["rule_detail"].update(self.render_rule_detail())
                    layout["proactive"].update(self.render_proactive())
                    layout["summary"].update(self.render_summary())
                    layout["footer"].update(self.render_footer(
                        "running" if not self._stop.is_set() else "stopped"
                    ))
                    time.sleep(0.25)
        except KeyboardInterrupt:
            self._stop.set()
            console.print("\n[yellow]Dashboard stopped[/yellow]")


def main():
    parser = argparse.ArgumentParser(description="Detection Dashboard")
    parser.add_argument("--demo", action="store_true", help="Run in demo mode")
    args = parser.parse_args()

    dashboard = DetectionDashboard(demo=args.demo)
    dashboard.run()


if __name__ == "__main__":
    main()