"""
Output formatting for task plans.

LEARNING NOTES:
- Separating formatting from data models follows "separation of concerns"
- The models know what the data IS; formatters know how to DISPLAY it
- This makes it easy to add new formats without touching model code

Supports multiple output formats:
- JSON: Machine-readable, good for piping to other tools or scripts
- Markdown: Human-readable, good for documentation or terminal display

Each formatter takes a TaskPlan and returns a formatted string.
"""

from .models import Priority, TaskPlan


def format_as_json(plan: TaskPlan, indent: int = 2) -> str:
    """
    Format the task plan as pretty-printed JSON.

    LEARNING NOTE:
    Pydantic models have a built-in model_dump_json() method that
    handles serialization of all types including:
    - datetime -> ISO format string
    - Enum -> string value
    - Nested models -> nested JSON objects

    Args:
        plan: The TaskPlan to format
        indent: Number of spaces for indentation (2 is readable but compact)

    Returns:
        JSON string representation
    """
    return plan.model_dump_json(indent=indent)


def format_as_markdown(plan: TaskPlan) -> str:
    """
    Format the task plan as a Markdown document.

    This creates a human-readable document with:
    - Headers for sections
    - Metadata (created date, total time estimate)
    - Numbered task list with details
    - Checkboxes for acceptance criteria (can be checked off in editors)

    Args:
        plan: The TaskPlan to format

    Returns:
        Markdown string representation
    """
    lines: list[str] = []

    # === Title ===
    lines.append(f"# {plan.title}")
    lines.append("")

    # === Metadata ===
    lines.append(f"**Created:** {plan.created_at.strftime('%Y-%m-%d %H:%M')}")
    if plan.total_estimated_hours:
        lines.append(f"**Estimated Time:** {plan.total_estimated_hours} hours")
    lines.append("")

    # === Summary ===
    lines.append("## Summary")
    lines.append("")
    lines.append(plan.summary)
    lines.append("")

    # === Original Request (as blockquote) ===
    lines.append("## Original Request")
    lines.append("")
    lines.append(f"> {plan.original_request}")
    lines.append("")

    # === Tasks ===
    lines.append("## Tasks")
    lines.append("")

    for i, task in enumerate(plan.tasks, start=1):
        # Task header with priority indicator
        priority_badge = _get_priority_badge(task.priority)
        lines.append(f"### {i}. {task.title} {priority_badge}")
        lines.append("")

        # Task description
        lines.append(task.description)
        lines.append("")

        # Task metadata as a bullet list
        if task.estimated_hours:
            lines.append(f"- **Estimated:** {task.estimated_hours} hours")

        if task.dependencies:
            deps = ", ".join(task.dependencies)
            lines.append(f"- **Dependencies:** {deps}")

        # Acceptance criteria as checkboxes
        if task.acceptance_criteria:
            lines.append("")
            lines.append("**Acceptance Criteria:**")
            for criterion in task.acceptance_criteria:
                # [ ] creates an unchecked checkbox in Markdown
                lines.append(f"- [ ] {criterion}")

        lines.append("")

    # === Assumptions ===
    if plan.assumptions:
        lines.append("## Assumptions")
        lines.append("")
        for assumption in plan.assumptions:
            lines.append(f"- {assumption}")
        lines.append("")

    # === Notes ===
    if plan.notes:
        lines.append("## Notes")
        lines.append("")
        lines.append(plan.notes)
        lines.append("")

    return "\n".join(lines)


def _get_priority_badge(priority: Priority) -> str:
    """
    Get a text badge indicating task priority.

    LEARNING NOTE:
    This is a "private" helper function (underscore prefix).
    It's only used by format_as_markdown().

    We use text badges instead of emojis because:
    1. Not all terminals render emojis well
    2. Text is more accessible
    3. It's clearer what the priority means

    Args:
        priority: The Priority enum value

    Returns:
        A string badge like "[HIGH]" or "[low]"
    """
    # Dictionary mapping Priority to badge text
    badge_map = {
        Priority.LOW: "[low]",
        Priority.MEDIUM: "[medium]",
        Priority.HIGH: "**[HIGH]**",
        Priority.CRITICAL: "**[CRITICAL]**",
    }

    return badge_map.get(priority, "")
