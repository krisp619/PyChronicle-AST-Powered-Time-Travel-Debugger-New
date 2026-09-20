from tracer_storage import TracerStorage


storage = TracerStorage()

storage.add_state(3, "total", 10)
storage.add_state(4, "total", 15)

print(storage.get_states())