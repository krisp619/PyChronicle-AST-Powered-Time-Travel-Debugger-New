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