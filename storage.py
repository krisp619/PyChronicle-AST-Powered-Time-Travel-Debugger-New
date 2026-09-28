"""
PyChronicle State Storage Engine
Optimized SQLite schema and storage manager for chronological execution steps and variable deltas.
"""

from __future__ import annotations
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ExecutionStep:
    step_id: int
    timestamp: float
    line_number: int
    func_name: str
    filename: str
    source_line: str
    event_type: str = "line"


@dataclass
class VariableDelta:
    step_id: int
    var_name: str
    value_repr: str
    type_name: str
    is_changed: bool = True


class StateStorage:
    """Fast in-memory or on-disk SQLite storage for execution time-travel."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Initializes tables and indexes for maximum lookup performance."""
        cursor = self.conn.cursor()
        
        # Pragmas for speed
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute("PRAGMA synchronous = NORMAL;")
        
        # Table 1: Execution steps
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_steps (
                step_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                line_number INTEGER NOT NULL,
                func_name TEXT NOT NULL,
                filename TEXT NOT NULL,
                source_line TEXT,
                event_type TEXT DEFAULT 'line'
            );
        """)

        # Table 2: Variable deltas (stores changes at each step)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS variable_deltas (
                delta_id INTEGER PRIMARY KEY AUTOINCREMENT,
                step_id INTEGER NOT NULL,
                var_name TEXT NOT NULL,
                value_repr TEXT NOT NULL,
                type_name TEXT NOT NULL,
                is_changed INTEGER DEFAULT 1,
                FOREIGN KEY (step_id) REFERENCES execution_steps(step_id)
            );
        """)

        # Table 3: Summary stats for audit & compression verification
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trace_metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)

        # Performance Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_steps_lineno ON execution_steps(line_number);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_deltas_step ON variable_deltas(step_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_deltas_var_step ON variable_deltas(var_name, step_id);")

        self.conn.commit()

    def record_step(
        self,
        line_number: int,
        func_name: str,
        filename: str,
        source_line: str = "",
        event_type: str = "line",
        timestamp: Optional[float] = None,
    ) -> int:
        """Inserts an execution step and returns its step_id."""
        if timestamp is None:
            timestamp = time.time()

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO execution_steps (timestamp, line_number, func_name, filename, source_line, event_type)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (timestamp, line_number, func_name, filename, source_line, event_type),
        )
        return cursor.lastrowid

    def record_variable_delta(
        self,
        step_id: int,
        var_name: str,
        value_repr: str,
        type_name: str,
        is_changed: bool = True,
    ) -> None:
        """Records a single variable mutation/delta."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO variable_deltas (step_id, var_name, value_repr, type_name, is_changed)
            VALUES (?, ?, ?, ?, ?)
            """,
            (step_id, var_name, value_repr, type_name, 1 if is_changed else 0),
        )

    def record_variable_deltas_batch(
        self,
        deltas: list[tuple[int, str, str, str, bool]],
    ) -> None:
        """Fast bulk insert of variable deltas."""
        if not deltas:
            return
        cursor = self.conn.cursor()
        cursor.executemany(
            """
            INSERT INTO variable_deltas (step_id, var_name, value_repr, type_name, is_changed)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(s, v, r, t, 1 if c else 0) for s, v, r, t, c in deltas],
        )

    def commit(self) -> None:
        """Commits pending transaction."""
        self.conn.commit()

    def get_step_count(self) -> int:
        """Returns total number of recorded steps."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM execution_steps")
        row = cursor.fetchone()
        return row[0] if row else 0

    def get_step(self, step_id: int) -> Optional[ExecutionStep]:
        """Retrieves a single execution step by its 1-based step_id."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT step_id, timestamp, line_number, func_name, filename, source_line, event_type "
            "FROM execution_steps WHERE step_id = ?",
            (step_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return ExecutionStep(
            step_id=row["step_id"],
            timestamp=row["timestamp"],
            line_number=row["line_number"],
            func_name=row["func_name"],
            filename=row["filename"],
            source_line=row["source_line"] or "",
            event_type=row["event_type"],
        )

    def get_all_steps(self) -> list[ExecutionStep]:
        """Returns all recorded execution steps in chronological order."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT step_id, timestamp, line_number, func_name, filename, source_line, event_type "
            "FROM execution_steps ORDER BY step_id ASC"
        )
        return [
            ExecutionStep(
                step_id=row["step_id"],
                timestamp=row["timestamp"],
                line_number=row["line_number"],
                func_name=row["func_name"],
                filename=row["filename"],
                source_line=row["source_line"] or "",
                event_type=row["event_type"],
            )
            for row in cursor.fetchall()
        ]

    def get_variables_at_step(self, step_id: int) -> dict[str, VariableDelta]:
        """
        Reconstructs the exact state of all variables at step_id by finding the
        most recent delta for each variable up to step_id.
        This provides instantaneous Time-Travel state reconstruction!
        """
        cursor = self.conn.cursor()
        # Subquery finds maximum step_id <= target step_id for each variable name
        cursor.execute(
            """
            WITH LatestDeltas AS (
                SELECT var_name, MAX(step_id) as latest_step
                FROM variable_deltas
                WHERE step_id <= ?
                GROUP BY var_name
            )
            SELECT vd.step_id, vd.var_name, vd.value_repr, vd.type_name, vd.is_changed
            FROM variable_deltas vd
            JOIN LatestDeltas ld ON vd.var_name = ld.var_name AND vd.step_id = ld.latest_step
            ORDER BY vd.var_name ASC
            """,
            (step_id,),
        )
        result: dict[str, VariableDelta] = {}
        for row in cursor.fetchall():
            result[row["var_name"]] = VariableDelta(
                step_id=row["step_id"],
                var_name=row["var_name"],
                value_repr=row["value_repr"],
                type_name=row["type_name"],
                is_changed=bool(row["is_changed"]),
            )
        return result

    def get_changed_variables_at_step(self, step_id: int) -> list[VariableDelta]:
        """Returns only the variables that actively changed at this exact step."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT step_id, var_name, value_repr, type_name, is_changed "
            "FROM variable_deltas WHERE step_id = ?",
            (step_id,),
        )
        return [
            VariableDelta(
                step_id=row["step_id"],
                var_name=row["var_name"],
                value_repr=row["value_repr"],
                type_name=row["type_name"],
                is_changed=bool(row["is_changed"]),
            )
            for row in cursor.fetchall()
        ]

    def get_variable_history(self, var_name: str) -> list[dict[str, Any]]:
        """
        Returns full history of a variable across all steps for 'Watch Variables' feature.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT s.step_id, s.line_number, s.timestamp, s.func_name, vd.value_repr, vd.type_name
            FROM variable_deltas vd
            JOIN execution_steps s ON vd.step_id = s.step_id
            WHERE vd.var_name = ?
            ORDER BY s.step_id ASC
            """,
            (var_name,),
        )
        return [
            {
                "step_id": row["step_id"],
                "line_number": row["line_number"],
                "timestamp": row["timestamp"],
                "func_name": row["func_name"],
                "value_repr": row["value_repr"],
                "type_name": row["type_name"],
            }
            for row in cursor.fetchall()
        ]

    def get_distinct_variable_names(self) -> list[str]:
        """Returns all tracked variable names across execution."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT var_name FROM variable_deltas ORDER BY var_name ASC")
        return [row[0] for row in cursor.fetchall()]

    def get_audit_stats(self, total_evaluated_vars: int = 0) -> dict[str, Any]:
        """Calculates storage audit stats including compression ratio."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM execution_steps")
        step_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM variable_deltas")
        delta_count = cursor.fetchone()[0]

        # Calculate theoretical uncompressed records if every variable was saved at every step
        uncompressed_records = total_evaluated_vars if total_evaluated_vars > 0 else (step_count * 10)
        compression_ratio = (
            ((uncompressed_records - delta_count) / uncompressed_records * 100)
            if uncompressed_records > delta_count
            else 0.0
        )

        return {
            "total_steps": step_count,
            "total_deltas_stored": delta_count,
            "uncompressed_potential_records": uncompressed_records,
            "compression_ratio_pct": round(compression_ratio, 2),
            "db_path": self.db_path,
        }

    def close(self) -> None:
        """Closes database connection."""
        self.conn.close()
