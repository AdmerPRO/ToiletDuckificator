# ToiletDuckificator

ToiletDuckificator is a configurable Python obfuscator for single files and whole folder-based projects. It can rename identifiers, hide literals, rewrite imports and loops, alias builtins, minify output, and optionally wrap everything in an encrypted runtime loader.

The project ships with:

- a Tkinter desktop GUI,
- a Python API for scripting and automation,
- support for obfuscating nested Python packages,
- tests covering the main transformations,
- example projects showing both simple and multi-file scenarios.

## Highlights

- Obfuscate a single `.py` file or an entire directory tree.
- Preserve nested package imports when module and folder names are renamed.
- Enable or disable every obfuscation stage independently.
- Generate separate output paths so the source files stay untouched.
- Run either from the GUI or directly from Python code.

## Project Structure

```text
ToiletDuckificator/
|-- toiletduckificator/
|   |-- __init__.py
|   |-- __main__.py
|   |-- gui.py
|   |-- name_generator.py
|   `-- obfuscator.py
|-- tests/
|   `-- test_obfuscator.py
|-- example_program/
|   |-- sample_app.py
|   `-- sample_app.duck.py
|-- example_folder_program/
|   |-- calculators.py
|   |-- main.py
|   |-- reports.py
|   `-- settings.py
|-- example_nested_program/
|   |-- core/
|   |   |-- __init__.py
|   |   |-- app_runner.py
|   |   `-- messages/
|   |       |-- __init__.py
|   |       |-- builder.py
|   |       `-- formatters.py
|   |-- main.py
|   `-- settings.py
|-- pyproject.toml
|-- requirements.txt
`-- LICENSE
```

## What Each File Does

### Core package

- `toiletduckificator/obfuscator.py`
  Contains the full transformation pipeline, output path logic, module renaming support, and the `ObfuscationOptions` settings object.
- `toiletduckificator/gui.py`
  Provides the desktop interface for choosing a file or folder, selecting an output location, and toggling each obfuscation stage.
- `toiletduckificator/name_generator.py`
  Generates safe random Python identifiers used during renaming.
- `toiletduckificator/__main__.py`
  Starts the GUI with `python -m toiletduckificator`.
- `toiletduckificator/__init__.py`
  Exposes the public API for importing the obfuscator in scripts.

### Tests

- `tests/test_obfuscator.py`
  Verifies identifier renaming, literals, imports, nested folders, runtime behavior preservation, and the new per-stage configuration flags.

### Example projects

- `example_program/`
  Small single-file example and one generated obfuscated output.
- `example_folder_program/`
  Flat multi-file example showing cross-module imports.
- `example_nested_program/`
  Nested package example with subpackages and internal imports.

## Installation

### Requirements

- Python 3.11 or newer
- A Tk-compatible Python installation if you want to use the GUI

### Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` installs the package in editable mode and adds `pytest` for local verification.

## Running the App

### GUI

```bash
python -m toiletduckificator.gui
```

You can also run the package entry point after installation:

```bash
toiletduckificator
```

### Python API

```python
from toiletduckificator import ObfuscationOptions, obfuscate_path, obfuscate_source

source = """
from reports import build_report

def main():
    return build_report("Duck")
"""

options = ObfuscationOptions(
    rename_identifiers=True,
    obfuscate_literals=True,
    rename_modules=False,
    rewrite_dynamic_imports=True,
    rewrite_for_loops=True,
    wrap_calls=True,
    alias_builtins=True,
    minify_output=True,
    encrypt_output=False,
)

obfuscated_source = obfuscate_source(source, options=options)
results = obfuscate_path("example_folder_program", "example_folder_program_duckified", options=options)
```

## Obfuscation Stages

Every stage can be turned on or off through `ObfuscationOptions` in code or by using the checkboxes in the GUI.

| Option | Default | What it does |
|---|---:|---|
| `rename_identifiers` | `True` | Renames local variables, parameters, functions, and selected private members. |
| `obfuscate_literals` | `True` | Rewrites integer literals and string literals inside collection literals. |
| `rename_modules` | `True` | Renames modules and folders in folder-based obfuscation runs and rewrites local import paths. |
| `rewrite_dynamic_imports` | `True` | Replaces direct imports with `__import__`/`getattr`-based dynamic assignments. |
| `rewrite_for_loops` | `True` | Converts eligible `for` loops into explicit iterator-driven `while` loops. |
| `wrap_calls` | `True` | Routes function calls through a generated wrapper function. |
| `alias_builtins` | `True` | Replaces common builtin names such as `print`, `len`, `sum`, or `open` with aliases. |
| `minify_output` | `True` | Compacts generated Python code before writing it out. |
| `encrypt_output` | `True` | Wraps the generated code inside a small runtime loader that decrypts and executes it. |

## Recommended Presets

### Maximum compatibility

Use this when you want lighter obfuscation and easier debugging:

```python
ObfuscationOptions(
    rename_identifiers=True,
    obfuscate_literals=False,
    rename_modules=False,
    rewrite_dynamic_imports=False,
    rewrite_for_loops=False,
    wrap_calls=False,
    alias_builtins=False,
    minify_output=False,
    encrypt_output=False,
)
```

### Full duck mode

Use this for the strongest built-in transformation chain:

```python
ObfuscationOptions()
```

## How Folder Obfuscation Works

When you pass a directory to `obfuscate_path(...)`, the tool:

1. finds every Python file recursively,
2. builds a new output layout,
3. optionally renames modules and package folders,
4. rewrites internal imports to match the new structure,
5. writes obfuscated files into a separate output tree.

Special filenames such as `main.py`, `start.py`, `app.py`, and `__init__.py` are preserved so entry points stay recognizable.

## Testing

```bash
python -m pytest
```

The test suite covers runtime behavior preservation, nested package handling, and the configuration switches that control the pipeline.

## Notes and Limitations

- The project currently targets Python source files only.
- The GUI depends on Tkinter being available in your Python installation.
- Obfuscation is designed to make source code harder to read, not to provide strong cryptographic protection.
- Dynamic runtime behavior, reflection-heavy code, or unusual import tricks may still need manual testing after obfuscation.

## License

This project is licensed under the MIT License. See `LICENSE` for details.
