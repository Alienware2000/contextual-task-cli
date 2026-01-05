"""
AI conversation management using the Anthropic Claude API.

LEARNING NOTES:
- This is the "heart" of the application - where AI magic happens
- We use the official Anthropic SDK which handles authentication, retries, etc.
- The conversation is "stateful" - we track message history for context
- Claude sees the full conversation history with each API call

This module handles:
- Multi-turn conversations with Claude
- Parsing Claude's structured JSON responses
- Managing conversation state (messages, question count, ready status)
- Generating the final task plan

The conversation flow:
1. User provides initial task description
2. Claude asks clarifying questions (structured JSON)
3. User answers questions
4. Repeat until Claude signals "ready" or max questions reached
5. Generate and return the task plan
"""

import json

from anthropic import Anthropic

from .config import get_settings
from .models import (
    ClarifyingQuestion,
    ConversationMessage,
    Priority,
    Task,
    TaskPlan,
)
from .prompts import get_plan_generation_prompt, get_system_prompt


class ConversationError(Exception):
    """
    Raised when there's an error in the conversation flow.

    LEARNING NOTE:
    Creating custom exceptions makes error handling clearer.
    Instead of catching generic Exception, callers can catch
    ConversationError specifically.
    """
    pass


class ConversationManager:
    """
    Manages the multi-turn conversation with Claude.

    LEARNING NOTE:
    This class uses the "state machine" pattern. The conversation moves
    through states:
        INITIAL -> QUESTIONING -> READY -> PLAN_GENERATED

    The instance variables track this state:
    - messages: The conversation history
    - questions_asked: Counter for limiting questions
    - is_ready: Whether Claude has enough info

    Example usage:
        manager = ConversationManager()

        # Start conversation with the task
        questions = manager.start("Build a REST API")

        # Answer questions in a loop
        while questions:
            for q in questions:
                answer = input(q.question)
            questions = manager.answer(answer)

        # Generate the plan
        plan = manager.generate_plan()
    """

    def __init__(self) -> None:
        """
        Initialize the conversation manager.

        LEARNING NOTE:
        We get settings here so any configuration errors fail early.
        The Anthropic client is created with our API key.
        """
        self.settings = get_settings()

        # Create the Anthropic API client
        # SecretStr.get_secret_value() returns the actual string
        self.client = Anthropic(
            api_key=self.settings.anthropic_api_key.get_secret_value()
        )

        # Conversation state
        self.messages: list[ConversationMessage] = []
        self.original_request: str = ""
        self.questions_asked: int = 0
        self.is_ready: bool = False
        self.understanding_summary: str = ""

    def start(self, task_description: str) -> list[ClarifyingQuestion]:
        """
        Start a new conversation with the initial task description.

        This resets all state and sends the first message to Claude.

        Args:
            task_description: The user's initial task description

        Returns:
            List of clarifying questions from Claude, or empty if ready
        """
        # Reset state for a new conversation
        self.original_request = task_description
        self.messages = []
        self.questions_asked = 0
        self.is_ready = False
        self.understanding_summary = ""

        # Add the user's initial message to history
        self.messages.append(ConversationMessage(
            role="user",
            content=f"I need help planning this task: {task_description}"
        ))

        # Get Claude's response (questions or ready signal)
        return self._get_claude_response()

    def answer(self, user_response: str) -> list[ClarifyingQuestion]:
        """
        Process the user's answer and get follow-up questions.

        This adds the user's response to the conversation history
        and asks Claude for the next set of questions (if any).

        Args:
            user_response: The user's answer to previous questions

        Returns:
            List of follow-up questions, or empty if ready to plan
        """
        # If already ready, no more questions needed
        if self.is_ready:
            return []

        # Add user's response to conversation history
        self.messages.append(ConversationMessage(
            role="user",
            content=user_response
        ))

        # Get Claude's next response
        return self._get_claude_response()

    def _get_claude_response(self) -> list[ClarifyingQuestion]:
        """
        Send the conversation to Claude and parse the response.

        LEARNING NOTE:
        This is a "private" method (underscore prefix is a Python convention).
        It's used internally by start() and answer().

        Returns:
            List of clarifying questions, or empty if ready
        """
        # Convert our message objects to the format Anthropic expects
        # Anthropic wants: [{"role": "user", "content": "..."}, ...]
        api_messages = [
            {"role": m.role, "content": m.content}
            for m in self.messages
        ]

        # Call the Claude API
        response = self.client.messages.create(
            model=self.settings.model_name,
            max_tokens=self.settings.max_tokens,
            system=get_system_prompt(self.settings.max_questions),
            messages=api_messages
        )

        # Extract the text content from Claude's response
        # response.content is a list of content blocks; we want the first text
        assistant_message = response.content[0].text

        # Add Claude's response to our conversation history
        self.messages.append(ConversationMessage(
            role="assistant",
            content=assistant_message
        ))

        # Parse the structured JSON response
        return self._parse_response(assistant_message)

    def _parse_response(self, response_text: str) -> list[ClarifyingQuestion]:
        """
        Parse Claude's JSON response into structured data.

        LEARNING NOTE:
        Claude is instructed to respond with JSON, but sometimes the JSON
        is wrapped in markdown code blocks (```json ... ```).
        We handle this gracefully with _extract_json().

        If parsing fails completely, we treat it as "ready" rather than
        crashing. This is "graceful degradation" - the show must go on.

        Args:
            response_text: Raw text response from Claude

        Returns:
            List of ClarifyingQuestion objects, or empty if ready/error
        """
        try:
            # Extract JSON from potential markdown formatting
            json_str = self._extract_json(response_text)
            data = json.loads(json_str)

            # Check if Claude signaled it has enough information
            if data.get("status") == "ready":
                self.is_ready = True
                self.understanding_summary = data.get("summary", "")
                return []

            # Parse the questions from the response
            questions = []
            for q_data in data.get("questions", []):
                questions.append(ClarifyingQuestion(
                    question=q_data["question"],
                    context=q_data.get("context"),
                    suggestions=q_data.get("suggestions", [])
                ))

            # Update question count
            self.questions_asked += len(questions)
            self.understanding_summary = data.get("understanding_so_far", "")

            # Check if we've hit the question limit
            if self.questions_asked >= self.settings.max_questions:
                self.is_ready = True

            return questions

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # If parsing fails, assume Claude is ready (graceful degradation)
            # This prevents the app from crashing on malformed responses
            self.is_ready = True
            self.understanding_summary = response_text
            return []

    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from text that may have markdown formatting.

        Claude often wraps JSON in markdown code blocks like:
            ```json
            {"status": "ready"}
            ```

        This function extracts just the JSON part.

        Args:
            text: Text potentially containing JSON in code blocks

        Returns:
            Extracted JSON string
        """
        # Try to find JSON in ```json ... ``` blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()

        # Try to find JSON in generic ``` ... ``` blocks
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()

        # Assume the entire response is JSON
        return text.strip()

    def generate_plan(self) -> TaskPlan:
        """
        Generate the final task plan based on the conversation.

        This is called after the Q&A phase is complete. It sends a new
        prompt to Claude asking it to generate a structured plan.

        Returns:
            Complete TaskPlan object

        Raises:
            ConversationError: If conversation isn't ready for plan generation
        """
        # Safety check: make sure we've had some conversation
        if not self.is_ready and self.questions_asked < 1:
            raise ConversationError(
                "Cannot generate plan: conversation not complete. "
                "Call start() and answer questions first."
            )

        # Build a summary of the conversation for the prompt
        conversation_summary = self._build_summary()

        # Create the plan generation prompt
        prompt = get_plan_generation_prompt(
            conversation_summary=conversation_summary,
            original_request=self.original_request
        )

        # Make a fresh API call for plan generation
        # (separate from the Q&A conversation)
        response = self.client.messages.create(
            model=self.settings.model_name,
            max_tokens=self.settings.max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )

        plan_json = response.content[0].text

        # Parse and validate the plan
        return self._parse_plan(plan_json)

    def _build_summary(self) -> str:
        """
        Build a human-readable summary of the conversation.

        This is included in the plan generation prompt so Claude
        has full context of what was discussed.

        Returns:
            Formatted conversation summary
        """
        summary_parts = []

        for msg in self.messages:
            # Label each message with who said it
            prefix = "User" if msg.role == "user" else "Assistant"
            summary_parts.append(f"{prefix}: {msg.content}")

        # Include the understanding summary if we have one
        if self.understanding_summary:
            summary_parts.append(
                f"\nCurrent Understanding: {self.understanding_summary}"
            )

        return "\n\n".join(summary_parts)

    def _parse_plan(self, plan_json: str) -> TaskPlan:
        """
        Parse Claude's JSON plan response into a TaskPlan object.

        LEARNING NOTE:
        This method handles the conversion from raw JSON to our
        Pydantic models. The tricky part is handling enums (Priority)
        which come as strings from JSON.

        Args:
            plan_json: JSON string from Claude

        Returns:
            Validated TaskPlan object

        Raises:
            ConversationError: If the plan can't be parsed
        """
        try:
            json_str = self._extract_json(plan_json)
            data = json.loads(json_str)

            # Parse each task, handling enum conversion
            tasks = []
            for task_data in data.get("tasks", []):
                # Convert priority string to enum
                # .lower() handles if Claude says "High" instead of "high"
                priority_str = task_data.get("priority", "medium").lower()
                try:
                    priority = Priority(priority_str)
                except ValueError:
                    # If invalid priority, default to medium
                    priority = Priority.MEDIUM

                tasks.append(Task(
                    title=task_data["title"],
                    description=task_data["description"],
                    priority=priority,
                    estimated_hours=task_data.get("estimated_hours"),
                    dependencies=task_data.get("dependencies", []),
                    acceptance_criteria=task_data.get("acceptance_criteria", [])
                ))

            # Create the TaskPlan with all parsed data
            return TaskPlan(
                title=data["title"],
                summary=data["summary"],
                original_request=data.get("original_request", self.original_request),
                tasks=tasks,
                assumptions=data.get("assumptions", []),
                notes=data.get("notes"),
                total_estimated_hours=data.get("total_estimated_hours")
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise ConversationError(
                f"Failed to parse task plan from Claude's response: {e}"
            )
