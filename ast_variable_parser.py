import ast
import sys
from dataclasses import dataclass, field
 
 
@dataclass
class Assignment:
    line_number: int
    variable_names: list       
    assignment_type: str       
    source_snippet: str        
 
 
class VariableAssignmentVisitor(ast.NodeVisitor):
    def __init__(self):
        self.assignments: list[Assignment] = []
 
    def _extract_names(self, target) -> list[str]:
        names = []
        if isinstance(target, ast.Name):
            names.append(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                names.extend(self._extract_names(elt))
        else:
            try:
                names.append(ast.unparse(target))
            except Exception:
                names.append(type(target).__name__)
        return names