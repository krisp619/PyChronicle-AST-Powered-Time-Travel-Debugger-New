"""
PyChronicle Terminal User Interface (TUI)
Built with Textual: Rich, interactive, hacker-style time-travel debugging dashboard.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Optional

from rich.text import Text
from rich.syntax import Syntax
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header,
    Footer,
    Static,
    DataTable,
    ProgressBar,
    Input,
    Label,
    Button,
)
from textual.reactive import reactive

from storage import StateStorage, ExecutionStep, VariableDelta


CSS_STYLES = """
Screen {
    background: #0d1117;
    color: #c9d1d9;
}

#header-bar {
    dock: top;
    height: 3;
    background: #161b22;
    border-bottom: heavy #00e5ff;
    padding: 0 1;
    content-align: center middle;
}

#header-title {
    color: #00e5ff;
    text-style: bold;
    width: 100%;
    text-align: center;
}

#main-layout {
    height: 1fr;
    margin: 0;
    padding: 0;
}

#left-pane {
    width: 60%;
    border: round #30363d;
    background: #0d1117;
    margin: 0 1;
    padding: 0 1;
}

#left-pane:focus-within {
    border: round #00e5ff;
}

#pane-title-code {
    background: #161b22;
    color: #58a6ff;
    text-style: bold;
    padding: 0 1;
    border-bottom: solid #30363d;
}

#code-scroll {
    height: 1fr;
    background: #0d1117;
}

#code-display {
    width: 100%;
    padding: 0 1;
}

#right-pane {
    width: 40%;
    margin-right: 1;
}

#variables-container {
    height: 60%;
    border: round #30363d;
    background: #0d1117;
    margin-bottom: 1;
}

#variables-container:focus-within {
    border: round #00e676;
}

#pane-title-vars {
    background: #161b22;
    color: #00e676;
    text-style: bold;
    padding: 0 1;
    border-bottom: solid #30363d;
}

#vars-table {
    height: 1fr;
    background: #0d1117;
}

#watch-container {
    height: 40%;
    border: round #30363d;
    background: #0d1117;
}

#watch-container:focus-within {
    border: round #ffd600;
}

#pane-title-watch {
    background: #161b22;
    color: #ffd600;
    text-style: bold;
    padding: 0 1;
    border-bottom: solid #30363d;
}

#watch-input {
    border: none;
    background: #161b22;
    color: #f0f6fc;
    margin: 0 1;
}

#watch-history-display {
    height: 1fr;
    padding: 0 1;
    color: #8b949e;
}

#timeline-pane {
    dock: bottom;
    height: 6;
    background: #161b22;
    border-top: heavy #00e5ff;
    padding: 0 1;
}

#timeline-header {
    height: 1;
    margin-top: 0;
}

#step-label {
    color: #00e5ff;
    text-style: bold;
    width: 50%;
}

#stats-label {
    color: #8b949e;
    width: 50%;
    text-align: right;
}

#timeline-progress {
    width: 100%;
    margin: 0;
}

#controls-bar {
    height: 1;
    color: #7ee787;
    text-align: center;
}
"""


class PyChronicleApp(App):
    """Interactive Time-Travel Debugger Terminal User Interface."""

    CSS = CSS_STYLES
    BINDINGS = [
        Binding("right", "step_forward", "Step Forward", priority=True, show=True),
        Binding("l", "step_forward", "Step Forward", priority=True, show=False),
        Binding("left", "step_backward", "Step Backward", priority=True, show=True),
        Binding("h", "step_backward", "Step Backward", priority=True, show=False),
        Binding("home", "jump_start", "Start", priority=True, show=True),
        Binding("end", "jump_end", "End", priority=True, show=True),
        Binding("space", "toggle_play", "Play/Pause", priority=True, show=True),
        Binding("w", "focus_watch", "Watch Variable", show=True),
        Binding("q", "quit", "Quit", priority=True, show=True),
    ]

    current_step_id = reactive(1)
    is_playing = reactive(False)
    watched_var = reactive("")

    def __init__(
        self,
        storage: StateStorage,
        target_path: str,
        audit_stats: Optional[dict[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.storage = storage
        self.target_path = Path(target_path).resolve()
        self.target_filename = self.target_path.name
        self.audit_stats = audit_stats or {}

        # Load target source lines
        if self.target_path.exists():
            self.source_lines = self.target_path.read_text(encoding="utf-8").splitlines()
        else:
            self.source_lines = []

        self.total_steps = max(1, self.storage.get_step_count())
        self._timer = None

    def compose(self) -> ComposeResult:
        """Constructs the TUI visual tree."""
        # Top banner
        with Container(id="header-bar"):
            yield Label(
                f"⚡ PyChronicle Time-Travel Debugger  |  Target: {self.target_filename}  |  Total Steps: {self.total_steps}",
                id="header-title",
            )

        # Main horizontal split
        with Horizontal(id="main-layout"):
            # Left: Source code display
            with Vertical(id="left-pane"):
                yield Label(f"📄 Source Code: {self.target_filename}", id="pane-title-code")
                with ScrollableContainer(id="code-scroll"):
                    yield Static("", id="code-display")

            # Right: Inspector (Variables + Watch)
            with Vertical(id="right-pane"):
                # Top Right: Variables Table
                with Vertical(id="variables-container"):
                    yield Label("📊 Variable State Inspector", id="pane-title-vars")
                    yield DataTable(id="vars-table")

                # Bottom Right: Watch Variables
                with Vertical(id="watch-container"):
                    yield Label("🔍 Watch Variable History", id="pane-title-watch")
                    yield Input(placeholder="Type variable name to track & press Enter...", id="watch-input")
                    with ScrollableContainer():
                        yield Static("Select or type a variable above to see its chronological mutations.", id="watch-history-display")

        # Bottom: Timeline Scrubbing Pane
        with Vertical(id="timeline-pane"):
            with Horizontal(id="timeline-header"):
                yield Label("Step: 1 / 1", id="step-label")
                comp_pct = self.audit_stats.get("compression_ratio_pct", 0.0)
                yield Label(f"Delta Compression: {comp_pct}% | Storage: SQLite", id="stats-label")
            yield ProgressBar(total=self.total_steps, show_percentage=True, id="timeline-progress")
            yield Label("Controls: [←/h] Prev Step | [→/l] Next Step | [Space] Play/Pause | [Home/End] Jump | [q] Quit", id="controls-bar")

    def on_mount(self) -> None:
        """Sets up DataTable columns and initial state on load."""
        table = self.query_one("#vars-table", DataTable)
        table.cursor_type = "row"
        table.add_column("Variable", width=14)
        table.add_column("Value", width=22)
        table.add_column("Type", width=10)
        table.add_column("Delta", width=10)

        # Set default watched variable if any exist
        distinct_vars = self.storage.get_distinct_variable_names()
        if distinct_vars:
            self.watched_var = distinct_vars[0]
            watch_input = self.query_one("#watch-input", Input)
            watch_input.value = self.watched_var

        # Render step 1
        self.update_ui_state()

    def watch_current_step_id(self, old_val: int, new_val: int) -> None:
        """Reactive watcher for current_step_id changes."""
        self.update_ui_state()

    def update_ui_state(self) -> None:
        """Refreshes all UI panes based on current_step_id."""
        if self.total_steps == 0:
            return

        step = self.storage.get_step(self.current_step_id)
        current_lineno = step.line_number if step else 1

        # 1. Update Timeline bar and label
        progress_bar = self.query_one("#timeline-progress", ProgressBar)
        progress_bar.progress = self.current_step_id

        pct = (self.current_step_id / self.total_steps) * 100
        step_label = self.query_one("#step-label", Label)
        step_label.update(f"⏳ Step: {self.current_step_id} / {self.total_steps} ({pct:.1f}%) | Line {current_lineno} ({step.func_name if step else ''})")

        # 2. Render Highlighted Source Code
        self._render_source_code(current_lineno)

        # 3. Update Variables Table
        self._render_variables_table()

        # 4. Update Watch Variable History
        self._render_watch_history()

    def _render_source_code(self, current_lineno: int) -> None:
        """Renders code with the active line prominently highlighted."""
        code_widget = self.query_one("#code-display", Static)
        text = Text()

        for idx, line in enumerate(self.source_lines, start=1):
            if idx == current_lineno:
                # Active line: High-contrast glowing highlight
                text.append(f" ▶ {idx:3d} │ ", style="bold black on #00e5ff")
                text.append(f"{line}\n", style="bold white on #1f2937")
            else:
                # Normal lines
                text.append(f"   {idx:3d} │ ", style="#484f58")
                text.append(f"{line}\n", style="#c9d1d9")

        code_widget.update(text)

        # Auto-scroll to keep active line in view
        scroll = self.query_one("#code-scroll", ScrollableContainer)
        line_height = 1
        scroll.scroll_to(y=max(0, current_lineno - 5), animate=False)

    def _render_variables_table(self) -> None:
        """Updates variables table with reconstructed state and delta badges."""
        table = self.query_one("#vars-table", DataTable)
        table.clear()

        # Get full reconstructed state at this step
        all_vars = self.storage.get_variables_at_step(self.current_step_id)
        # Get active changes at this step
        changed_vars = {vd.var_name for vd in self.storage.get_changed_variables_at_step(self.current_step_id)}

        for var_name, var_delta in all_vars.items():
            is_active_delta = var_name in changed_vars
            delta_label = Text("⚡ MUTATED", style="bold #ffd600") if is_active_delta else Text("—", style="#484f58")
            name_text = Text(var_name, style="bold #58a6ff" if is_active_delta else "white")
            val_text = Text(var_delta.value_repr, style="#7ee787" if is_active_delta else "#c9d1d9")
            type_text = Text(var_delta.type_name, style="#a371f7")

            table.add_row(name_text, val_text, type_text, delta_label)

    def _render_watch_history(self) -> None:
        """Renders chronological history for watched variable."""
        display = self.query_one("#watch-history-display", Static)
        if not self.watched_var:
            display.update(Text("Type a variable name above to watch its history.", style="#8b949e"))
            return

        history = self.storage.get_variable_history(self.watched_var)
        if not history:
            display.update(Text(f"Variable '{self.watched_var}' was never modified during execution.", style="#ff7b72"))
            return

        text = Text()
        text.append(f"Chronological mutations of '{self.watched_var}':\n", style="bold #ffd600")

        for entry in history:
            is_current = (entry["step_id"] <= self.current_step_id)
            marker = "●" if entry["step_id"] == self.current_step_id else ("✓" if is_current else "○")
            style = "bold #00e676" if entry["step_id"] == self.current_step_id else ("#58a6ff" if is_current else "#484f58")

            text.append(f" {marker} Step {entry['step_id']:3d} (L{entry['line_number']:2d}): ", style=style)
            text.append(f"{entry['value_repr']}\n", style="bold white" if is_current else "#6e7681")

        display.update(text)

    def _is_input_focused(self) -> bool:
        try:
            return self.focused == self.query_one("#watch-input", Input)
        except Exception:
            return False

    # User Interactions & Key Actions
    def action_step_forward(self) -> None:
        """Step one frame forward in time."""
        if self._is_input_focused():
            return
        if self.current_step_id < self.total_steps:
            self.current_step_id += 1

    def action_step_backward(self) -> None:
        """Step one frame backward in time."""
        if self._is_input_focused():
            return
        if self.current_step_id > 1:
            self.current_step_id -= 1

    def action_jump_start(self) -> None:
        """Jump to the very first step."""
        if self._is_input_focused():
            return
        self.current_step_id = 1

    def action_jump_end(self) -> None:
        """Jump to the final step."""
        if self._is_input_focused():
            return
        self.current_step_id = self.total_steps

    def action_toggle_play(self) -> None:
        """Toggles automatic playback of execution steps."""
        if self._is_input_focused():
            return
        self.is_playing = not self.is_playing
        if self.is_playing:
            self._timer = self.set_interval(0.1, self._play_step)
        else:
            if self._timer:
                self._timer.stop()
                self._timer = None

    def _play_step(self) -> None:
        """Timer callback for auto-play replay."""
        if self.current_step_id < self.total_steps:
            self.current_step_id += 1
        else:
            self.action_toggle_play()

    def action_focus_watch(self) -> None:
        """Brings focus to watch variable input."""
        self.query_one("#watch-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handles user submitting a watch variable name."""
        val = event.value.strip()
        if val:
            self.watched_var = val
            self._render_watch_history()
