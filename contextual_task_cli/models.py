"""
Pydantic models for task plan data structures.

LEARNING NOTES:
- Pydantic models are classes that validate data automatically
- They convert JSON/dicts to typed Python objects
- They provide automatic serialization (to_json, to_dict)
- Type hints aren't just documentation - Pydantic enforces them!

These models define the schema for:
- Individual tasks within a plan
- The complete task plan output
- Questions asked during the conversation
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Priority(str, Enum):
    """
    Task priority levels.

    LEARNING NOTE:
    This is a "str Enum" - it inherits from both str and Enum.
    This means Priority.HIGH == "high" is True, making JSON serialization easy.
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Task completion status for tracking progress."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class Task(BaseModel):
    """
    Represents a single actionable task within a plan.

    LEARNING NOTE:
    - Field() lets you add metadata like descriptions and defaults
    - Optional fields use `| None` (Python 3.10+ syntax for Optional)
    - default_factory=list creates a NEW empty list for each instance
      (using default=[] would share the same list across all instances - a common bug!)

    Example:
        task = Task(
            title="Set up project structure",
            description="Create directories and initial files",
            priority=Priority.HIGH,
            estimated_hours=1.0
        )
    """

    title: str = Field(
        description="Short, actionable task title (start with a verb)"
    )

    description: str = Field(
        description="Detailed description of what needs to be done"
    )

    priority: Priority = Field(
        default=Priority.MEDIUM,
        description="Task priority level"
    )

    estimated_hours: float | None = Field(
        default=None,
        description="Estimated time to complete in hours"
    )

    dependencies: list[str] = Field(
        default_factory=list,
        description="List of task titles this task depends on"
    )

    acceptance_criteria: list[str] = Field(
        default_factory=list,
        description="Criteria to determine when task is complete"
    )

    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        description="Current task status"
    )


class TaskPlan(BaseModel):
    """
    Complete task plan generated from the conversation.

    This is the primary output model. After Claude asks questions and
    understands your task, it generates a TaskPlan containing:
    - Metadata about the plan (title, summary)
    - The original request for reference
    - Ordered list of actionable tasks
    - Assumptions made during planning
    - Additional notes/recommendations

    LEARNING NOTE:
    Pydantic models can contain other Pydantic models (like tasks: list[Task]).
    Validation is recursive - each Task in the list is also validated.
    """

    title: str = Field(
        description="Overall plan title"
    )

    summary: str = Field(
        description="Brief summary of what was discussed and the approach taken"
    )

    original_request: str = Field(
        description="The user's original task description (for reference)"
    )

    tasks: list[Task] = Field(
        default_factory=list,
        description="Ordered list of tasks to complete"
    )

    assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions made during planning (important to document!)"
    )

    notes: str | None = Field(
        default=None,
        description="Additional notes or recommendations"
    )

    total_estimated_hours: float | None = Field(
        default=None,
        description="Total estimated time for all tasks"
    )

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When the plan was generated"
    )

    def calculate_total_hours(self) -> float | None:
        """
        Calculate total hours from individual task estimates.

        LEARNING NOTE:
        Pydantic models are just Python classes - you can add methods!
        This method sums up task estimates, ignoring tasks without estimates.
        """
        estimates = [t.estimated_hours for t in self.tasks if t.estimated_hours]
        return sum(estimates) if estimates else None


class ConversationMessage(BaseModel):
    """
    Represents a single message in the conversation history.

    Used internally to track the back-and-forth with Claude.
    The role is either "user" or "assistant" (Claude).
    """

    role: str = Field(
        description="Either 'user' or 'assistant'"
    )

    content: str = Field(
        description="The message content"
    )


class ClarifyingQuestion(BaseModel):
    """
    A structured question that Claude asks the user.

    Instead of Claude just asking "What's your timeline?" as plain text,
    it returns structured questions. This allows us to:
    - Display context for why the question is being asked
    - Show suggested answers to help the user
    - Build a better UX with Rich formatting

    LEARNING NOTE:
    Structuring data like this (instead of raw strings) is a key pattern.
    It separates "what the data is" from "how to display it".
    """

    question: str = Field(
        description="The question to ask the user"
    )

    context: str | None = Field(
        default=None,
        description="Why this question is being asked (helps user understand)"
    )

    suggestions: list[str] = Field(
        default_factory=list,
        description="Suggested answers or examples to help the user"
    )
