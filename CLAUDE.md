# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Guidelines

- Use Python 3
- Minimize external dependencies; prefer the standard library
- Prioritize simplicity, clarity, and readability over performance
- Use type hints throughout
- Use `unittest` for testing
- Use Pydantic for data validation and type enforcement

## Environment

- Python 3.13 virtual environment at `.qaenv/`
- Activate: `source .qaenv/bin/activate`
- Install dependencies: `pip install -r requirements.txt` (once a requirements file exists)

## Linting

```bash
pylint <module_or_file>
```

The `.pylintrc` follows the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html). Key rules enforced:

- 80-character line limit (URLs and import lines are exempt)
- 4-space indentation
- `snake_case` for functions, variables, arguments, and attributes; `PascalCase` for classes; `UPPER_SNAKE_CASE` for module-level constants
- Consistent quote characters within a module
- Docstrings required on non-test functions/classes with 12+ lines (test functions, `main`, and dunder methods are exempt)
- The entire `R` (refactor) category is disabled; `fixme`, `global-statement`, `wrong-import-order`, and many Python 2 compatibility checks are also disabled
