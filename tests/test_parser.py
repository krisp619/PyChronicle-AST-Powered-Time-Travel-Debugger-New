import ast
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from ast_variable_parser import VariableAssignmentVisitor


def test_parser(file_path):
    source = Path(file_path).read_text()
    tree = ast.parse(source)

    visitor = VariableAssignmentVisitor()
    visitor.visit(tree)

    for assignment in visitor.assignments:
        print(assignment)


test_parser("tests/sample_scripts/multiple_assignment_test.py")
