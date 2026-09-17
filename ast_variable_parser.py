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

    def visit_For(self, node: ast.For):
        names = self._extract_names(node.target)
        self.assignments.append(Assignment(
            line_number=node.lineno,
            variable_names=names,
            assignment_type="For",
            source_snippet=f"for {ast.unparse(node.target)} in {ast.unparse(node.iter)}:",
        ))
        self.generic_visit(node)
 
    def visit_With(self, node: ast.With):
        for item in node.items:
            if item.optional_vars is not None:
                names = self._extract_names(item.optional_vars)
                self.assignments.append(Assignment(
                    line_number=node.lineno,
                    variable_names=names,
                    assignment_type="With",
                    source_snippet=ast.unparse(node).splitlines()[0],
                ))
        self.generic_visit(node)

def parse_file(filepath: str) -> list[Assignment]:
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
 
    tree = ast.parse(source, filename=filepath)
    visitor = VariableAssignmentVisitor()
    visitor.visit(tree)
    return sorted(visitor.assignments, key=lambda a: a.line_number)

def main():
    if len(sys.argv) != 2:
        print("Usage: python ast_variable_parser.py <target_script.py>")
        sys.exit(1)
 
    target = sys.argv[1]
    assignments = parse_file(target)
 
    print(f"\nFound {len(assignments)} variable assignment(s) in {target}:\n")
    print(f"{'Line':<6} {'Type':<10} {'Variable(s)':<20} Source")
    print("-" * 70)
    for a in assignments:
        vars_str = ", ".join(a.variable_names)
        print(f"{a.line_number:<6} {a.assignment_type:<10} {vars_str:<20} {a.source_snippet}")
 
 
if __name__ == "__main__":
    main()