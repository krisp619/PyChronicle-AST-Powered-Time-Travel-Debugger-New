class Calculator:
    def __init__(self, value):
        self.value = value

    def add(self, number):
        result = self.value + number
        return result

calculator = Calculator(10)
output = calculator.add(5)