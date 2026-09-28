"""
Tests for PyChronicle Textual TUI using Textual's async headless testing runner.
"""

import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from storage import StateStorage
from tracer import ExecutionTracer
from ui import PyChronicleApp


class TestPyChronicleUI(unittest.IsolatedAsyncioTestCase):
    async def test_ui_scaffolding_and_scrubbing(self):
        storage = StateStorage(":memory:")
        tracer = ExecutionTracer("sample.py", storage=storage, enable_compression=True)
        storage, stats = tracer.run()

        app = PyChronicleApp(storage, "sample.py", audit_stats=stats)

        async with app.run_test() as pilot:
            # 1. Initial Step is 1
            self.assertEqual(app.current_step_id, 1)

            # 2. Step forward
            await pilot.press("right")
            self.assertEqual(app.current_step_id, 2)

            # 3. Jump to end
            await pilot.press("end")
            self.assertEqual(app.current_step_id, app.total_steps)

            # 4. Step backward
            await pilot.press("left")
            self.assertEqual(app.current_step_id, app.total_steps - 1)

            # 5. Jump to start
            await pilot.press("home")
            self.assertEqual(app.current_step_id, 1)

            # 6. Change watch variable
            watch_input = app.query_one("#watch-input")
            watch_input.value = "counter"
            watch_input.focus()
            await pilot.press("enter")
            await pilot.pause()
            self.assertEqual(app.watched_var, "counter")

        storage.close()


if __name__ == "__main__":
    unittest.main()
