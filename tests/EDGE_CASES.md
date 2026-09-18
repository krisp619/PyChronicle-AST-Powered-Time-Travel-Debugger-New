# AST Parser Edge Cases

## 1. Chained Assignment

Input:
a = b = c = 10

Result:
Passed - detected a, b, and c.

## 2. Tuple Assignment

Input:
a, b = 10, 20

Result:
Passed - detected a and b.

## 3. Nested Tuple Assignment

Input:
a, (b, c) = 10, (20, 30)

Result:
Passed - detected a, b, and c.

## 4. Attribute Assignment

Input:
person.name = "Chandana"

Result:
Passed - detected person.name.

## 5. Subscript Assignment

Input:
numbers[0] = 100

Result:
Passed - detected numbers[0].

## 6. For Loop Assignment

Input:
for i in range(5):
    total = total + i

Result:
Passed - loop assignments detected.

## 7. Function Assignment

Result:
Passed - function assignments detected.

## 8. Class Assignment

Result:
Passed - class-related assignments detected.

## 9. Augmented Assignment

Input:

total = 10
total += 5

Result:

Passed - detected total with AugAssign.


## 10. Annotated Assignment

Input:

count: int = 10

Result:

Passed - detected count with AnnAssign.


## 11. Dictionary Assignment

Input:

data = {}
data["name"] = "Chandana"

Result:

Passed - detected data and data["name"].


## 12. Multiple Assignment

Input:

a, b, c = [10, 20, 30]

Result:

Passed - detected a, b, and c.


## 13. With Statement

Input:

with open("test.txt", "w") as file:
    file.write("Hello")

Result:

Passed - detected file variable from the with statement.