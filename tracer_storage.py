import sqlite3
import time


class TracerStorage:
    def __init__(self, database_name="pychronicle.db"):
        self.states = []

        self.connection = sqlite3.connect(database_name)

        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS execution_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                line_number INTEGER,
                variable_name TEXT,
                serialized_value TEXT
            )
        """)

        self.connection.commit()

    def add_state(self, line_number, variable_name, value):
        state = {
            "line_number": line_number,
            "variable_name": variable_name,
            "value": value
        }

       
        self.states.append(state)

        self.connection.execute(
        """
        INSERT INTO execution_state
        (timestamp, line_number, variable_name, serialized_value)
        VALUES (?, ?, ?, ?)
        """,
        (time.time(), line_number, variable_name, str(value))
    )

        self.connection.commit()

    def get_states(self):
        return self.states