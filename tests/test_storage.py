import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import unittest
from storage import StateStorage, ExecutionStep, VariableDelta


class TestStateStorage(unittest.TestCase):
    def setUp(self):
        self.storage = StateStorage(":memory:")

    def tearDown(self):
        self.storage.close()

    def test_record_steps_and_retrieve(self):
        step1 = self.storage.record_step(line_number=10, func_name="main", filename="test.py", source_line="x = 1")
        step2 = self.storage.record_step(line_number=11, func_name="main", filename="test.py", source_line="y = 2")
        self.storage.commit()

        self.assertEqual(self.storage.get_step_count(), 2)
        
        s1 = self.storage.get_step(step1)
        self.assertIsNotNone(s1)
        self.assertEqual(s1.line_number, 10)
        self.assertEqual(s1.source_line, "x = 1")

    def test_variable_deltas_and_time_travel_reconstruction(self):
        # Step 1: x = 10, y = 20
        s1 = self.storage.record_step(line_number=1, func_name="run", filename="sample.py", source_line="x = 10; y = 20")
        self.storage.record_variable_delta(s1, "x", "10", "int")
        self.storage.record_variable_delta(s1, "y", "20", "int")

        # Step 2: x = 15 (y not changed)
        s2 = self.storage.record_step(line_number=2, func_name="run", filename="sample.py", source_line="x = 15")
        self.storage.record_variable_delta(s2, "x", "15", "int")

        # Step 3: z = 99 (x and y unchanged)
        s3 = self.storage.record_step(line_number=3, func_name="run", filename="sample.py", source_line="z = 99")
        self.storage.record_variable_delta(s3, "z", "99", "int")

        self.storage.commit()

        # Check time travel at Step 1: x should be 10, y should be 20, z not present
        state_at_1 = self.storage.get_variables_at_step(s1)
        self.assertEqual(state_at_1["x"].value_repr, "10")
        self.assertEqual(state_at_1["y"].value_repr, "20")
        self.assertNotIn("z", state_at_1)

        # Check time travel at Step 2: x should be 15, y should still be 20, z not present
        state_at_2 = self.storage.get_variables_at_step(s2)
        self.assertEqual(state_at_2["x"].value_repr, "15")
        self.assertEqual(state_at_2["y"].value_repr, "20")
        self.assertNotIn("z", state_at_2)

        # Check time travel at Step 3: x=15, y=20, z=99
        state_at_3 = self.storage.get_variables_at_step(s3)
        self.assertEqual(state_at_3["x"].value_repr, "15")
        self.assertEqual(state_at_3["y"].value_repr, "20")
        self.assertEqual(state_at_3["z"].value_repr, "99")

    def test_variable_history(self):
        s1 = self.storage.record_step(1, "main", "test.py")
        self.storage.record_variable_delta(s1, "counter", "0", "int")
        s2 = self.storage.record_step(2, "main", "test.py")
        self.storage.record_variable_delta(s2, "counter", "1", "int")
        s3 = self.storage.record_step(3, "main", "test.py")
        self.storage.record_variable_delta(s3, "counter", "2", "int")
        self.storage.commit()

        history = self.storage.get_variable_history("counter")
        self.assertEqual(len(history), 3)
        self.assertEqual([h["value_repr"] for h in history], ["0", "1", "2"])


if __name__ == "__main__":
    unittest.main()
