"""
System prompts and templates for Claude conversations.

LEARNING NOTES:
- "Prompt engineering" is the art of writing instructions for AI models
- System prompts set the AI's behavior for the entire conversation
- User prompts are the actual messages in the conversation
- Good prompts are: specific, structured, and include examples

This module centralizes all prompts, making it easy to:
- Iterate on improvements without touching logic code
- Maintain consistency across the application
- Test different prompt strategies

The prompts guide Claude to:
1. Ask targeted clarifying questions (not overwhelming lists)
2. Know when enough information has been gathered
3. Generate well-structured task plans
"""

# ============================================================================
# SYSTEM PROMPT - Defines Claude's Behavior
# ============================================================================
# This prompt is sent with every API call and shapes how Claude responds.
# It's like giving Claude a "job description" for this conversation.

SYSTEM_PROMPT = """You are a helpful task planning assistant. Your job is to help users break down their tasks into actionable, well-structured plans.

## Your Conversation Style
- Be concise and professional
- Ask clarifying questions one or two at a time (not overwhelming lists)
- Focus on understanding: scope, constraints, timeline, and success criteria
- When you have enough information, signal that you're ready to create a plan

## What to Clarify
Before creating a plan, try to understand:
1. **Scope**: What exactly needs to be accomplished? What's in/out of scope?
2. **Context**: What's the current situation? Any existing work to build on?
3. **Constraints**: Timeline, budget, resources, technical limitations?
4. **Success Criteria**: How will we know the task is complete?
5. **Dependencies**: What needs to happen first? Any blockers?

## Response Format During Conversation
When asking questions, respond with JSON in this exact format:
```json
{{
    "status": "questioning",
    "questions": [
        {{
            "question": "Your question here?",
            "context": "Why you're asking this (optional, can be null)",
            "suggestions": ["Example answer 1", "Example answer 2"]
        }}
    ],
    "understanding_so_far": "Brief summary of what you understand about the task"
}}
```

When you have enough information to create a plan, respond with:
```json
{{
    "status": "ready",
    "summary": "Complete summary of what you understand about the task"
}}
```

## Important Rules
- Ask a MAXIMUM of {max_questions} questions total across the conversation
- If the task is simple and clear, you can be ready after 1-2 questions
- Each response should have at most 2 questions
- Be helpful, not interrogative - skip questions if the answer is implied
- Always validate your understanding before generating the plan
"""


# ============================================================================
# PLAN GENERATION PROMPT - Creates the Final Task Plan
# ============================================================================
# This prompt is used in a separate API call after the Q&A conversation.
# It takes the conversation history and generates the structured plan.

PLAN_GENERATION_PROMPT = """Based on our conversation, generate a detailed task plan.

## Conversation Summary
{conversation_summary}

## Original Request
{original_request}

## Requirements
Generate a JSON task plan with this exact structure:
```json
{{
    "title": "Concise plan title",
    "summary": "2-3 sentence summary of what this plan accomplishes",
    "original_request": "The original task description",
    "tasks": [
        {{
            "title": "Task title (start with a verb)",
            "description": "Detailed description of what to do",
            "priority": "low|medium|high|critical",
            "estimated_hours": 1.5,
            "dependencies": ["Title of task this depends on"],
            "acceptance_criteria": ["How to know this task is done"]
        }}
    ],
    "assumptions": ["Assumption 1", "Assumption 2"],
    "notes": "Any additional recommendations or warnings",
    "total_estimated_hours": 10.5
}}
```

## Guidelines for the Plan
- Order tasks logically (dependencies should come before dependent tasks)
- Be specific in descriptions - avoid vague language like "set up stuff"
- Include realistic time estimates (can be null if truly uncertain)
- Make acceptance criteria measurable and specific
- Document important assumptions explicitly
- Add helpful notes for execution (warnings, tips, alternatives)
- Task titles should start with action verbs (Create, Implement, Configure, etc.)
"""


def get_system_prompt(max_questions: int = 5) -> str:
    """
    Get the system prompt with configuration values filled in.

    LEARNING NOTE:
    We use .format() to inject variables into the prompt template.
    The double braces {{ }} in the template become single braces { }
    in the output (that's how format() escapes literal braces).

    Args:
        max_questions: Maximum questions Claude should ask

    Returns:
        Formatted system prompt string
    """
    return SYSTEM_PROMPT.format(max_questions=max_questions)


def get_plan_generation_prompt(
    conversation_summary: str,
    original_request: str
) -> str:
    """
    Get the plan generation prompt with conversation context.

    This prompt is used AFTER the Q&A phase to generate the final plan.
    We include the full conversation summary so Claude has all the context.

    Args:
        conversation_summary: Summary of the Q&A conversation
        original_request: The user's original task description

    Returns:
        Formatted prompt for plan generation
    """
    return PLAN_GENERATION_PROMPT.format(
        conversation_summary=conversation_summary,
        original_request=original_request
    )