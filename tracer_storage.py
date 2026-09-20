class TracerStorage:
    def __init__(self):
        self.states = []

    def add_state(self, line_number, variable_name, value):
        state = {
            "line_number": line_number,
            "variable_name": variable_name,
            "value": value
        }

        self.states.append(state)

    def get_states(self):
        return self.states