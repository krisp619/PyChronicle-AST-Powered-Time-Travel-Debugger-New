# PyChronicle: AST-Powered Time-Travel Debugger

> **Project 1 - Advanced Python Engineering | Infotact Solutions**  
> *Developer Tools & Metaprogramming*

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![TUI](https://img.shields.io/badge/TUI-Textual-green.svg)](https://textual.textualize.io/)
[![Storage](https://img.shields.io/badge/Storage-In--Memory%20SQLite-yellow.svg)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen.svg)]()

---

## 🚀 Overview

Standard Python debuggers (like `pdb` or IDE debuggers) are **linear**—you step forward line-by-line until you find a bug. If you miss the exact moment a variable mutated incorrectly, you have to restart the entire execution.

**PyChronicle** is a **"Time-Travel" Execution Tracer**. Utilizing Python's `ast` (Abstract Syntax Tree) module and `sys.settrace`, it wraps an entire application's execution and records the chronological **delta state** of every variable at every line of code into a fast, in-memory **SQLite database**. 

Using an interactive Terminal User Interface (built with **Textual**), developers can slide a timeline backward and forward, observing the exact historical state of the application without ever having to re-run the code.

---

## 🌟 Core Architecture & Key Modules

```
                    ┌─────────────────────────┐
                    │ Target Python Script    │
                    └───────────┬─────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
┌───────────────────────────────┐       ┌───────────────────────────────┐
│ AST Variable Parser           │       │ Execution Engine Tracer       │
│ (ast_variable_parser.py)      │       │ (tracer.py)                   │
│ • Detects static assignments  │       │ • sys.settrace line hook      │
│ • Assign, AugAssign, For, etc.│       │ • Safe object serialization   │
└───────────────────────────────┘       │ • 80-90% Delta Compression    │
                                        └───────────────┬───────────────┘
                                                        │
                                                        ▼
                                        ┌───────────────────────────────┐
                                        │ Fast SQLite State Storage     │
                                        │ (storage.py)                  │
                                        │ • execution_steps table       │
                                        │ • variable_deltas table       │
                                        │ • Fast time-travel query      │
                                        └───────────────┬───────────────┘
                                                        │
                        ┌───────────────────────────────┴───────────────────────────────┐
                        ▼                                                               ▼
        ┌───────────────────────────────┐                               ┌───────────────────────────────┐
        │ Terminal User Interface (TUI) │                               │ Command Line Interface (CLI)  │
        │ (ui.py)                       │                               │ (cli.py)                      │
        │ • Code View & Active Line     │                               │ • pychronicle run <script>    │
        │ • Timeline Scrubber Slider    │                               │ • pychronicle audit <script>  │
        │ • Variable Inspector & Deltas │                               │ • pychronicle parse <script>  │
        │ • "Watch Variables" History   │                               └───────────────────────────────┘
        └───────────────────────────────┘
```

### 1. AST Variable Parser (`ast_variable_parser.py`)
Parses target Python scripts and statically identifies all variable assignments, including basic assignments (`a = 1`), augmented assignments (`a += 1`), type-annotated assignments (`a: int = 1`), for-loop target unpacking (`for x in iterable:`), and context manager targets (`with open(...) as f:`).

### 2. Execution Tracer with Delta Compression (`tracer.py`)
Uses `sys.settrace` to record runtime execution step-by-step. Implements **Delta Compression**: instead of storing the entire state tree at every line, it compares against prior frame values and only records variables that were modified or introduced at that specific step. This reduces database overhead by **up to 90%**.

### 3. State Storage Engine (`storage.py`)
An optimized In-Memory / File SQLite database with indexing on `line_number` and `(var_name, step_id)`. Offers sub-millisecond historical state reconstruction for any step $N$:
$$\text{State}(N) = \bigcup_{v \in \text{Variables}} \text{LatestDelta}(v, \text{step} \le N)$$

### 4. Hacker-Style Terminal UI (`ui.py`)
Built using Textual with a high-contrast dark theme:
- **Highlighted Source Code Pane**: Centered and auto-scrolling with current line indicator (`▶`).
- **Variables State Table**: Displays live values, data types, and glowing `⚡ MUTATED` delta badges.
- **Watch Variables History**: Enter any variable name to view its step-by-step evolution over time.
- **Interactive Timeline Scrubber**: Step forward, backward, jump to start/end, or auto-play execution.

### 5. CLI Utility & Packaging (`cli.py`, `setup.py`, `pyproject.toml`)
Packaged as a command-line tool accessible via `pychronicle`.

---

## 💻 Installation

Clone the repository and install in editable mode:

```bash
git clone https://github.com/krisp619/PyChronicle-AST-Powered-Time-Travel-Debugger-New.git
cd PyChronicle-AST-Powered-Time-Travel-Debugger-New
pip install -e .
```

Dependencies:
- `click >= 8.0`
- `rich >= 13.0`
- `textual >= 0.50`

---

## 🛠️ Usage

### 1. Interactive Time-Travel Debugger (TUI)
```bash
pychronicle run sample.py
```
Or directly with Python:
```bash
python . run sample.py
```

#### TUI Keyboard Shortcuts:
| Key | Action |
| :--- | :--- |
| **`→`** or **`l`** | Step 1 frame forward in time |
| **`←`** or **`h`** | Step 1 frame backward in time |
| **`Home`** | Jump to initial execution step |
| **`End`** | Jump to final execution step |
| **`Space`** | Toggle auto-play replay animation |
| **`w`** | Focus **Watch Variable** input box |
| **`q`** | Quit debugger |

---

### 2. Headless Trace Execution
Run without launching the TUI to generate execution metrics:
```bash
pychronicle run sample.py --no-ui
```

Output:
```
[PyChronicle Tracing] sample.py
PyChronicle Time-Travel Active: final counter = 30
  PyChronicle Execution Trace Summary  
┌─────────────────────────┬───────────┐
│ Metric                  │ Value     │
├─────────────────────────┼───────────┤
│ Target Script           │ sample.py │
│ Total Execution Steps   │ 84        │
│ Variable Deltas Stored  │ 60        │
│ Delta Compression Ratio │ 79.31%    │
│ Execution Time          │ 0.0099s   │
│ Database Storage        │ :memory:  │
└─────────────────────────┴───────────┘
```

---

### 3. Static AST Variable Parser
Inspect all detected static variable targets before running:
```bash
pychronicle parse sample.py
```

---

### 4. Storage & Delta Compression Audit
Run Mid-Project review audit to compare compressed delta storage vs full-state baseline:
```bash
pychronicle audit sample.py
```

---

## 🧪 Testing & Validation

The test suite covers unit tests, tracer loop validation (1,000+ iterations without dropped frames), storage audit, and async TUI interactions:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

All 7 test suites pass in < 2 seconds:
- `tests/test_parser.py`: AST static assignment parsing and edge cases
- `tests/test_storage.py`: SQLite schema, indexing, and time-travel reconstruction
- `tests/test_tracer_and_audit.py`: Complex loop frame preservation, throughput benchmark, delta compression validation
- `tests/test_ui.py`: Textual async testing runner, keybindings, timeline scrubbing, and variable watching

---

## 📋 Development Roadmap Status (Weeks 1 - 4)

- [x] **Week 1 Core Engineering:** AST variable assignment parsing (`VariableAssignmentVisitor`)
- [x] **Week 1 Storage:** Fast SQLite schema with chronological variable deltas
- [x] **Week 2 Tracer Engine:** `sys.settrace` execution flow recording
- [x] **Week 2 TUI Scaffolding:** Textual app with split panes and timeline bar
- [x] **Mid-Project Review:** Loop validation without dropping frames & storage throughput audit
- [x] **Week 3 Delta Compression:** 80-90% memory reduction via delta tracking
- [x] **Week 3 Time-Scrubbing UI:** Real-time synchronized line highlighting and state inspection
- [x] **Week 4 Packaging:** CLI tool (`click`) with `pychronicle run`, `audit`, and `parse`
- [x] **Week 4 Polish:** "Watch Variables" feature, Play/Pause animation, and hacker-style aesthetics
