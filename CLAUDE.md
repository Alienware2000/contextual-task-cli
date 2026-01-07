# Contextual Task CLI

An AI-powered command-line tool that helps users break down tasks into actionable plans through conversational Q&A with Claude.

## Project Overview

This CLI takes a task description, asks clarifying questions via Claude AI, and outputs a structured task plan in Markdown or JSON format.

**Repository:** https://github.com/Alienware2000/contextual-task-cli

## Tech Stack

- **Python 3.10+**
- **Typer** - CLI framework
- **Rich** - Beautiful terminal output
- **Pydantic** - Data validation and models
- **pydantic-settings** - Environment variable management
- **Anthropic SDK** - Claude API integration

## Project Structure

```
contextual_task_cli/
├── main.py          # CLI entry point (Typer commands)
├── config.py        # Settings from environment (pydantic-settings)
├── models.py        # Pydantic models (Task, TaskPlan, etc.)
├── prompts.py       # System prompts for Claude
├── conversation.py  # ConversationManager class (API logic)
├── formatters.py    # Output formatting (JSON/Markdown)
├── __init__.py      # Package marker + version
└── __main__.py      # Enables: python -m contextual_task_cli
```

## Commands

```bash
# Run the CLI
task-cli plan "Your task description"
task-cli plan                           # Interactive mode
task-cli plan -f json -o plan.json      # JSON output to file
task-cli plan -s "Simple task"          # Skip questions

# Other commands
task-cli config                         # Show current config
task-cli version                        # Show version
```

## Environment Variables

Required in `.env` file:
```
TASK_CLI_ANTHROPIC_API_KEY=sk-ant-...
```

Optional:
```
TASK_CLI_MODEL_NAME=claude-sonnet-4-5-20250929
TASK_CLI_MAX_TOKENS=4096
TASK_CLI_MAX_QUESTIONS=5
```

## Development

```bash
# Install in dev mode
pip install -e .

# Run directly
python -m contextual_task_cli plan "test"
```

## Code Patterns

- **ConversationManager** uses state machine pattern (INITIAL → QUESTIONING → READY → PLAN_GENERATED)
- **Settings** uses singleton pattern via `get_settings()`
- **Prompts** use template variables with `.format()`
- **Error handling** catches specific Anthropic exceptions with user-friendly messages

## Related

This project was built as part of a learning curriculum. See the companion repo:
- https://github.com/Alienware2000/learn-cli
