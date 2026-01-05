"""
Entry point for running the package as a module.

LEARNING NOTES:
- __main__.py is executed when you run: python -m contextual_task_cli
- This is an alternative to the `task-cli` command defined in pyproject.toml
- Useful during development before installing the package

Usage:
    $ python -m contextual_task_cli plan "My task"
    $ python -m contextual_task_cli --help
"""

from .main import app

if __name__ == "__main__":
    app()
