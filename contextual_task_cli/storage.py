"""
Storage module for saving and loading task plans.

ARCHITECTURE NOTES:
- This module handles ALL file system operations for plans
- main.py calls these functions but doesn't know HOW they work
- Uses formatters.py for converting plans to JSON/Markdown strings
- Uses models.py to reconstruct TaskPlan objects when loading

Single Responsibility: This file ONLY deals with persistence (saving/loading).
"""

import json
from datetime import date
from pathlib import Path

from .formatters import format_as_json, format_as_markdown
from .models import TaskPlan


def get_plans_directory() -> Path:
    """
    Get the path to ~/.task-cli/plans/, creating it if needed.

    Why ~/.task-cli/?
    - Standard Unix convention for app data
    - Survives project deletions
    - Single location for all plans
    """
    plans_dir = Path.home() / ".task-cli" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    return plans_dir


def generate_filename(plan: TaskPlan) -> str:
    """
    Generate a filename from a plan: '2026-01-07_build-rest-api'

    Why this format?
    - Date prefix: sorts chronologically
    - Slug from title: human-readable
    - No extension: we add .json/.md when saving
    """
    today = date.today().isoformat()
    # Convert title to URL-friendly slug
    slug = plan.title.lower().replace(" ", "-")
    # Remove characters that are problematic in filenames
    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        slug = slug.replace(char, '')
    return f"{today}_{slug}"


def save_plan(plan: TaskPlan) -> Path:
    """
    Save a plan as both JSON and Markdown.

    Returns the base path (without extension) so caller can inform user.

    Why both formats?
    - JSON: machine-readable, can be loaded back into Python
    - Markdown: human-readable, can open in any editor
    """
    plans_dir = get_plans_directory()
    filename = generate_filename(plan)

    # Save JSON (source of truth)
    json_path = plans_dir / f"{filename}.json"
    json_path.write_text(format_as_json(plan))

    # Save Markdown (human-readable copy)
    md_path = plans_dir / f"{filename}.md"
    md_path.write_text(format_as_markdown(plan))

    return plans_dir / filename  # Return base path


def list_plans() -> list[dict]:
    """
    List all saved plans with their metadata.

    Returns list of dicts with 'filename', 'title', 'created' for display.
    Only looks at .json files (source of truth).
    """
    plans_dir = get_plans_directory()
    plans = []

    for json_file in sorted(plans_dir.glob("*.json"), reverse=True):
        try:
            data = json.loads(json_file.read_text())
            plans.append({
                "filename": json_file.stem,  # filename without extension
                "title": data.get("title", "Unknown"),
                "created": data.get("created_at", "Unknown"),
                "path": json_file,
            })
        except (json.JSONDecodeError, KeyError):
            # Skip corrupted files
            continue

    return plans


def load_plan(filename: str) -> TaskPlan:
    """
    Load a plan from JSON file back into a TaskPlan object.

    Args:
        filename: Either just the name ('2026-01-07_my-plan')
                  or full path to .json file

    This is why we save as JSON - Pydantic can reconstruct the full object!
    """
    plans_dir = get_plans_directory()

    # Handle both 'filename' and 'filename.json'
    if not filename.endswith('.json'):
        filename = f"{filename}.json"

    json_path = plans_dir / filename

    if not json_path.exists():
        raise FileNotFoundError(f"Plan not found: {json_path}")

    data = json.loads(json_path.read_text())
    return TaskPlan.model_validate(data)  # Pydantic reconstructs the object!
