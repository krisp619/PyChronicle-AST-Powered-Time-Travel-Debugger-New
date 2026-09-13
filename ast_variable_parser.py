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

    def visit_Assign(self, node: ast.Assign):
        names = []
        for target in node.targets:
            names.extend(self._extract_names(target))
        self.assignments.append(Assignment(
            line_number=node.lineno,
            variable_names=names,
            assignment_type="Assign",
            source_snippet=ast.unparse(node),
        ))
        self.generic_visit(node)
 
    def visit_AugAssign(self, node: ast.AugAssign):
        names = self._extract_names(node.target)
        self.assignments.append(Assignment(
            line_number=node.lineno,
            variable_names=names,
            assignment_type="AugAssign",
            source_snippet=ast.unparse(node),
        ))
        self.generic_visit(node)
 
    def visit_AnnAssign(self, node: ast.AnnAssign):
        names = self._extract_names(node.target)
        self.assignments.append(Assignment(
            line_number=node.lineno,
            variable_names=names,
            assignment_type="AnnAssign",
            source_snippet=ast.unparse(node),
        ))
        self.generic_visit(node)