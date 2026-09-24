import sys
import time
import runpy
from dataclasses import dataclass, field
 
 
@dataclass
class TraceRecord:
    timestamp: float
    line_number: int
    variable_name: str
    value: str          
 
 
class Tracer:
    def __init__(self, target_filepath: str):
        self.target_filepath = target_filepath
        self.records: list[TraceRecord] = []
        self._last_snapshot: dict = {}   
 
    def _serialize(self, value) -> str:
        try:
            return repr(value)
        except Exception:
            return f"<unrepresentable {type(value).__name__}>"

    def _trace_function(self, frame, event, arg):
        if frame.f_code.co_filename != self.target_filepath:
            return self._trace_function  

        if event == "line":
            line_no = frame.f_lineno
            current_locals = frame.f_locals

            for var_name, value in current_locals.items():
                if var_name.startswith("__") and var_name.endswith("__"):
                    continue
                serialized = self._serialize(value)
                self.records.append(TraceRecord(
                    timestamp=time.time(),
                    line_number=line_no,
                    variable_name=var_name,
                    value=serialized,
                ))

        return self._trace_function

    def run(self):
        sys.settrace(self._trace_function)
        try:
            runpy.run_path(self.target_filepath, run_name="__main__")
        finally:
            sys.settrace(None)

def main():
    if len(sys.argv) != 2:
        print("Usage: python tracer.py <target_script.py>")
        sys.exit(1)
 
    target = sys.argv[1]
    tracer = Tracer(target)
    tracer.run()
 
    print(f"\nCaptured {len(tracer.records)} variable snapshots "
          f"across execution of {target}:\n")
    print(f"{'Line':<6} {'Variable':<15} Value")
    print("-" * 60)
    for r in tracer.records:
        print(f"{r.line_number:<6} {r.variable_name:<15} {r.value}")
 
 
if __name__ == "__main__":
    main()