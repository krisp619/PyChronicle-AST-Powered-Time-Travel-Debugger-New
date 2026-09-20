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