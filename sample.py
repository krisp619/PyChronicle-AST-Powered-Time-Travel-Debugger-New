"""
PyChronicle Demo Sample Script
Demonstrates variables, loops, calculations, and mutations for Time-Travel debugging.
"""


def calculate_factorial(n: int) -> int:
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result


def main():
    message = "PyChronicle Time-Travel Active"
    threshold = 5
    counter = 0
    history = []

    for step in range(1, 6):
        counter += step * 2
        fact = calculate_factorial(step)
        history.append({"step": step, "counter": counter, "fact": fact})

    status = "Execution Completed Successfully"
    print(f"{message}: final counter = {counter}")


if __name__ == "__main__":
    main()