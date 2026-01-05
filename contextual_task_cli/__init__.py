"""
Contextual Task CLI - AI-powered task planning assistant.

LEARNING NOTES:
- __init__.py makes a directory a "package" that can be imported
- It's also a good place to define what gets exported when someone imports your package
- __version__ is a convention for storing package version
- __all__ lists what gets imported with "from package import *"

This package provides a CLI tool that uses Claude AI to help users
break down tasks into structured, actionable plans through
intelligent conversation.

CLI Usage:
    $ task-cli plan "Build a REST API"
    $ task-cli plan --format json -o plan.json

Programmatic Usage:
    from contextual_task_cli import ConversationManager, TaskPlan

    manager = ConversationManager()
    questions = manager.start("My task description")
    # ... answer questions ...
    plan = manager.generate_plan()
"""

__version__ = "0.1.0"
__author__ = "Your Name"

# Re-export key classes for programmatic use
# This allows: from contextual_task_cli import TaskPlan
from .conversation import ConversationManager
from .formatters import format_as_json, format_as_markdown
from .models import Priority, Task, TaskPlan

__all__ = [
    # Version info
    "__version__",
    "__author__",
    # Models
    "TaskPlan",
    "Task",
    "Priority",
    # Core functionality
    "ConversationManager",
    # Formatters
    "format_as_json",
    "format_as_markdown",
]
