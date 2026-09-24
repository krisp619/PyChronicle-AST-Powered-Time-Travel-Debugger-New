# Tracer SQLite Storage

## Purpose

This module stores tracer execution records in SQLite so that
captured variable states can be retrieved later.

## Stored Data

Each execution state contains:

- Line number
- Variable name
- Serialized value

## Storage Flow

Tracer
→ TracerStorage
→ SQLite database
→ Execution state records

## Testing

The SQLite integration test verifies that:

1. Tracer records are captured.
2. Tracer records are stored in SQLite.
3. The number of tracer records matches the SQLite records.
4. Stored variable data can be verified.
5. The integration test completes successfully.

## Test File

`tests/test_tracer_sqlite_integration.py`

The test uses `sample.py` as the target Python script.

## Result

The tracer-to-SQLite integration test passed successfully.