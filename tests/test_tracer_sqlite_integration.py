import sys
from pathlib import Path

from tracer import Tracer
from tracer_storage import TracerStorage


target_file = Path("sample.py").resolve()

tracer = Tracer(str(target_file))
storage = TracerStorage(":memory:")

sys.settrace(tracer._trace_function)

try:
    code = compile(
        target_file.read_text(),
        str(target_file),
        "exec"
    )
    exec(code, {})
finally:
    sys.settrace(None)


for record in tracer.records:
    storage.add_state(
        record.line_number,
        record.variable_name,
        record.value
    )


cursor = storage.connection.execute(
    """
    SELECT line_number, variable_name, serialized_value
    FROM execution_state
    """
)

rows = cursor.fetchall()

print("Tracer records:", len(tracer.records))
print("SQLite records:", len(rows))
print("SQLite data:", rows)

assert len(tracer.records) == len(rows)
assert len(rows) > 0

print("Integration test passed!")