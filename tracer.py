"""
PyChronicle Execution Engine & Tracer
Uses sys.settrace to intercept execution flow, capture frame states,
and record variable mutations into SQLite with Delta Compression.
"""

from __future__ import annotations
import inspect
import linecache
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional

from storage import StateStorage


# Internal Python dunder attributes to exclude from user variable tracking
IGNORED_VARIABLE_NAMES = {
    "__name__",
    "__doc__",
    "__package__",
    "__loader__",
    "__spec__",
    "__annotations__",
    "__builtins__",
    "__file__",
    "__cached__",
}


def safe_serialize(value: Any, max_len: int = 500) -> tuple[str, str]:
    """
    Safely serializes a Python object into (value_repr, type_name).
    Guaranteed not to raise an exception even for problematic __repr__ implementations.
    """
    type_name = type(value).__name__
    try:
        val_repr = repr(value)
        if len(val_repr) > max_len:
            val_repr = val_repr[:max_len] + f"... (truncated, length={len(val_repr)})"
    except Exception as e:
        val_repr = f"<{type_name} unprintable: {e}>"
    return val_repr, type_name


class ExecutionTracer:
    """
    Time-Travel Execution Tracer.
    Hooks into Python's runtime via sys.settrace, filters execution to the target script,
    and logs chronological execution steps and variable deltas into SQLite.
    """

    def __init__(
        self,
        target_path: str,
        storage: Optional[StateStorage] = None,
        enable_compression: bool = True,
    ):
        self.target_path = Path(target_path).resolve()
        self.target_filename = self.target_path.name
        self.storage = storage or StateStorage(":memory:")
        self.enable_compression = enable_compression

        # Cache target script source lines
        if self.target_path.exists():
            self.source_lines = self.target_path.read_text(encoding="utf-8").splitlines()
        else:
            self.source_lines = []

        # Delta tracking state per function/frame
        self._last_known_vars: dict[str, str] = {}
        self.total_var_evaluations: int = 0
        self.total_deltas_recorded: int = 0
        self.is_tracing: bool = False
        self._error: Optional[Exception] = None

    def _get_source_line(self, lineno: int) -> str:
        """Returns the trimmed source line for given 1-indexed line number."""
        if 1 <= lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1].strip()
        return ""

    def _is_target_frame(self, frame) -> bool:
        """Checks if the frame belongs to the target script."""
        try:
            frame_path = Path(frame.f_code.co_filename).resolve()
            return frame_path == self.target_path
        except Exception:
            return False

    def _trace_dispatch(self, frame, event: str, arg: Any):
        """Main trace callback invoked by sys.settrace."""
        # Only trace code in our target script file
        if not self._is_target_frame(frame):
            return self._trace_dispatch

        if event in ("line", "return"):
            lineno = frame.f_lineno
            func_name = frame.f_code.co_name
            source_line = self._get_source_line(lineno)

            # Record step in database
            step_id = self.storage.record_step(
                line_number=lineno,
                func_name=func_name,
                filename=self.target_filename,
                source_line=source_line,
                event_type=event,
                timestamp=time.time(),
            )

            # Extract local variables
            # In Python 3.13+, frame.f_locals can be a proxy; dict() converts it cleanly
            current_locals = dict(frame.f_locals)
            deltas_to_insert = []

            for var_name, var_value in current_locals.items():
                if var_name in IGNORED_VARIABLE_NAMES:
                    continue

                self.total_var_evaluations += 1
                serialized_repr, type_name = safe_serialize(var_value)

                if self.enable_compression:
                    # Delta Compression: Only record if value has changed or is new
                    prev_repr = self._last_known_vars.get(var_name)
                    if prev_repr != serialized_repr:
                        deltas_to_insert.append((step_id, var_name, serialized_repr, type_name, True))
                        self._last_known_vars[var_name] = serialized_repr
                        self.total_deltas_recorded += 1
                else:
                    # Uncompressed mode (for benchmarking / audits)
                    deltas_to_insert.append((step_id, var_name, serialized_repr, type_name, True))
                    self.total_deltas_recorded += 1

            if deltas_to_insert:
                self.storage.record_variable_deltas_batch(deltas_to_insert)

        return self._trace_dispatch

    def run(self, script_args: Optional[list[str]] = None) -> tuple[StateStorage, dict[str, Any]]:
        """
        Executes the target script under trace supervision.
        Returns the populated StateStorage and audit performance stats.
        """
        if not self.target_path.exists():
            raise FileNotFoundError(f"Target script not found: {self.target_path}")

        # Prepare execution globals
        script_globals = {
            "__name__": "__main__",
            "__file__": str(self.target_path),
            "__doc__": None,
            "__builtins__": __builtins__,
        }

        # Backup system state
        old_argv = sys.argv[:]
        old_path = sys.path[:]
        sys.argv = [str(self.target_path)] + (script_args or [])
        sys.path.insert(0, str(self.target_path.parent))

        code_text = self.target_path.read_text(encoding="utf-8")
        compiled_code = compile(code_text, str(self.target_path), "exec")

        self.is_tracing = True
        self._last_known_vars.clear()
        self.total_var_evaluations = 0
        self.total_deltas_recorded = 0

        # Start execution under trace
        sys.settrace(self._trace_dispatch)
        start_time = time.perf_counter()
        try:
            exec(compiled_code, script_globals, script_globals)
        except Exception as e:
            self._error = e
        finally:
            sys.settrace(None)
            self.is_tracing = False
            elapsed_time = time.perf_counter() - start_time
            sys.argv = old_argv
            sys.path = old_path
            self.storage.commit()

        stats = self.storage.get_audit_stats(self.total_var_evaluations)
        stats["execution_time_seconds"] = round(elapsed_time, 4)
        stats["target_script"] = str(self.target_path)
        stats["compression_enabled"] = self.enable_compression
        if self._error:
            stats["runtime_error"] = str(self._error)

        return self.storage, stats
