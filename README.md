# Contextual Task CLI

An AI-powered CLI tool that helps you break down tasks into structured, actionable plans through intelligent conversation.

## How It Works

1. You describe a task
2. The AI asks clarifying questions to understand scope, constraints, and requirements
3. You answer the questions
4. The AI generates a detailed task plan with prioritized steps

## Installation

```bash
# Clone the repository
cd contextual-task-cli

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e .
```

## Configuration

Create a `.env` file in the project root (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:

```
TASK_CLI_ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

Get your API key from: https://console.anthropic.com/

## Usage

### Interactive Mode

```bash
# Start interactive planning (prompts for task description)
task-cli plan
```

### Direct Task Description

```bash
# Provide task directly
task-cli plan "Build a REST API for user management"
```

### Output Options

```bash
# JSON output
task-cli plan -f json "My task"

# Save to file
task-cli plan -o plan.md "My task"

# JSON output to file
task-cli plan -f json -o plan.json "My task"
```

### Skip Questions

```bash
# Generate plan immediately without clarifying questions
task-cli plan -s "Simple task"
```

### Other Commands

```bash
# Show current configuration
task-cli config

# Show version
task-cli version

# Show help
task-cli --help
task-cli plan --help
```

## Project Structure

```
contextual-task-cli/
├── pyproject.toml              # Project config and dependencies
├── .env.example                # Template for environment variables
├── README.md                   # This file
│
└── contextual_task_cli/        # Main package
    ├── __init__.py             # Package exports
    ├── __main__.py             # python -m support
    ├── main.py                 # CLI commands (Typer)
    ├── config.py               # Settings management
    ├── models.py               # Data models (Pydantic)
    ├── conversation.py         # AI conversation logic
    ├── formatters.py           # Output formatting
    └── prompts.py              # AI prompts
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy contextual_task_cli

# Linting
ruff check contextual_task_cli
```

## License

MIT
