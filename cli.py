"""
PyChronicle CLI Entry Point
Command-line interface built with Click for running, auditing, and inspecting
time-travel debugging sessions.
"""

from __future__ import annotations
import sys
from pathlib import Path

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ast_variable_parser import parse_assignments_from_file
from storage import StateStorage
from tracer import ExecutionTracer
from ui import PyChronicleApp

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="PyChronicle")
def main():
    """PyChronicle: AST-Powered Time-Travel Debugger for Python."""
    pass


@main.command()
@click.argument("script", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--no-ui", is_flag=True, default=False, help="Run headlessly without launching Textual TUI.")
@click.option("--db", type=str, default=":memory:", help="SQLite database path (default: in-memory).")
@click.option("--no-compression", is_flag=True, default=False, help="Disable delta compression.")
@click.option("--watch", "watch_var", type=str, default=None, help="Initial variable to watch.")
@click.argument("script_args", nargs=-1, type=click.UNPROCESSED)
def run(script: Path, no_ui: bool, db: str, no_compression: bool, watch_var: str | None, script_args: tuple):
    """Executes SCRIPT with time-travel tracing and launches interactive TUI."""
    console.print(f"[bold cyan][PyChronicle Tracing][/] [yellow]{script}[/]")

    storage = StateStorage(db)
    tracer = ExecutionTracer(
        target_path=str(script),
        storage=storage,
        enable_compression=not no_compression,
    )

    try:
        storage, stats = tracer.run(script_args=list(script_args))
    except Exception as e:
        console.print(f"[bold red]Execution error:[/] {e}")
        sys.exit(1)

    step_count = storage.get_step_count()
    if step_count == 0:
        console.print("[yellow]Warning: Target script finished with 0 recorded steps.[/]")
        return

    if no_ui:
        # Headless summary report
        table = Table(title="PyChronicle Execution Trace Summary", border_style="cyan")
        table.add_column("Metric", style="bold white")
        table.add_column("Value", style="green")

        table.add_row("Target Script", str(script))
        table.add_row("Total Execution Steps", str(stats["total_steps"]))
        table.add_row("Variable Deltas Stored", str(stats["total_deltas_stored"]))
        table.add_row("Delta Compression Ratio", f"{stats['compression_ratio_pct']}%")
        table.add_row("Execution Time", f"{stats['execution_time_seconds']}s")
        table.add_row("Database Storage", stats["db_path"])

        console.print(table)
    else:
        # Launch Textual TUI
        app = PyChronicleApp(
            storage=storage,
            target_path=str(script),
            audit_stats=stats,
        )
        if watch_var:
            app.watched_var = watch_var
        app.run()


@main.command()
@click.argument("script", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def parse(script: Path):
    """Parses SCRIPT Abstract Syntax Tree (AST) to identify variable assignments."""
    console.print(f"[bold cyan]AST Analysis for:[/] [yellow]{script}[/]\n")
    assignments = parse_assignments_from_file(str(script))

    table = Table(title=f"Static AST Variable Assignments ({len(assignments)} found)", border_style="blue")
    table.add_column("Line", justify="right", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Variables", style="bold green")
    table.add_column("Source Snippet", style="white")

    for a in assignments:
        table.add_row(
            str(a.line_number),
            a.assignment_type,
            ", ".join(a.variable_names),
            a.source_snippet,
        )

    console.print(table)


@main.command()
@click.argument("script", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def audit(script: Path):
    """Performs Mid-Project Storage & Compression Audit on SCRIPT."""
    console.print(f"[bold cyan]Benchmarking trace storage and delta compression on:[/] [yellow]{script}[/]\n")

    # Run 1: Compressed
    tracer_comp = ExecutionTracer(str(script), storage=StateStorage(":memory:"), enable_compression=True)
    storage_comp, stats_comp = tracer_comp.run()

    # Run 2: Uncompressed
    tracer_uncomp = ExecutionTracer(str(script), storage=StateStorage(":memory:"), enable_compression=False)
    storage_uncomp, stats_uncomp = tracer_uncomp.run()

    table = Table(title="PyChronicle Storage & Delta Audit", border_style="green")
    table.add_column("Metric", style="bold white")
    table.add_column("Delta Compressed", style="bold cyan")
    table.add_column("Uncompressed Full State", style="bold red")

    table.add_row("Execution Steps", str(stats_comp["total_steps"]), str(stats_uncomp["total_steps"]))
    table.add_row("Variable Records Stored", str(stats_comp["total_deltas_stored"]), str(stats_uncomp["total_deltas_stored"]))
    savings = (stats_uncomp["total_deltas_stored"] - stats_comp["total_deltas_stored"])
    savings_pct = (savings / max(1, stats_uncomp["total_deltas_stored"])) * 100
    table.add_row("Memory / Storage Saved", f"{savings} records ({savings_pct:.1f}%)", "0% (Baseline)")
    table.add_row("Execution Time", f"{stats_comp['execution_time_seconds']}s", f"{stats_uncomp['execution_time_seconds']}s")

    console.print(table)


if __name__ == "__main__":
    main()
