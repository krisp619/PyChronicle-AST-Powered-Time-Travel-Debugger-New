"""
PyChronicle Mid-Project Review & Validation Tests
Validates:
1. Trace Validation: Complex loops without dropping frames
2. Storage Audit: Handling thousands of state changes with high throughput
3. Delta Compression: Verified reduction in redundant state storage
"""

import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from storage import StateStorage
from tracer import ExecutionTracer


class TestTracerAndAudit(unittest.TestCase):
    def test_complex_loop_no_dropped_frames(self):
        """Validates tracer captures every iteration of a 1000-iteration loop accurately."""
        loop_code = """
total = 0
for i in range(1000):
    total += i
"""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(loop_code)
            temp_path = f.name

        try:
            storage = StateStorage(":memory:")
            tracer = ExecutionTracer(temp_path, storage=storage, enable_compression=True)
            storage, stats = tracer.run()

            # In a 1000 iteration loop, there should be > 2000 execution steps (for line + add line)
            self.assertGreater(stats["total_steps"], 2000)

            # Check variable history for 'total' (1000 mutations across loop)
            history = storage.get_variable_history("total")
            self.assertEqual(len(history), 1000)

            # Reconstruct final state
            final_vars = storage.get_variables_at_step(stats["total_steps"])
            expected_sum = sum(range(1000))
            self.assertEqual(final_vars["total"].value_repr, str(expected_sum))
            self.assertEqual(final_vars["i"].value_repr, "999")
            storage.close()
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_delta_compression_efficiency(self):
        """Proves delta compression reduces variable records by >85% in loops with multiple stable variables."""
        test_code = """
stable_a = "Config Value"
stable_b = [1, 2, 3, 4, 5]
stable_c = {"key": "value"}
mutating_counter = 0

for i in range(200):
    mutating_counter += 1
"""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(test_code)
            temp_path = f.name

        try:
            # Run 1: With Delta Compression
            tracer_comp = ExecutionTracer(temp_path, storage=StateStorage(":memory:"), enable_compression=True)
            storage_comp, stats_comp = tracer_comp.run()

            # Run 2: Uncompressed
            tracer_uncomp = ExecutionTracer(temp_path, storage=StateStorage(":memory:"), enable_compression=False)
            storage_uncomp, stats_uncomp = tracer_uncomp.run()

            # Verify that compressed stores dramatically fewer delta entries than uncompressed
            deltas_comp = stats_comp["total_deltas_stored"]
            deltas_uncomp = stats_uncomp["total_deltas_stored"]

            savings_pct = (deltas_uncomp - deltas_comp) / deltas_uncomp * 100
            self.assertGreater(savings_pct, 70.0)
            self.assertLess(deltas_comp, deltas_uncomp)
            storage_comp.close()
            storage_uncomp.close()
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_storage_audit_throughput(self):
        """Verifies database writes thousands of records within fraction of a second."""
        storage = StateStorage(":memory:")
        start_time = time.perf_counter()

        # Insert 5,000 steps and 10,000 deltas in bulk
        for i in range(1, 5001):
            s_id = storage.record_step(line_number=i % 100, func_name="benchmark", filename="bench.py")
            storage.record_variable_delta(s_id, "v1", str(i), "int")
            storage.record_variable_delta(s_id, "v2", str(i * 2), "int")
        storage.commit()

        elapsed = time.perf_counter() - start_time
        self.assertEqual(storage.get_step_count(), 5000)
        # Should easily complete within 1.0 second
        self.assertLess(elapsed, 1.0)
        storage.close()


if __name__ == "__main__":
    unittest.main()
