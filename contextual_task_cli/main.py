"""
Main CLI entry point using Typer.

LEARNING NOTES:
- Typer is a modern CLI framework that uses Python type hints
- Type hints like `str`, `int`, `bool` automatically become CLI arguments
- The Annotated[] syntax adds metadata (help text, defaults, validation)
- Rich (included with typer[all]) provides beautiful terminal formatting

This module defines the command-line interface:
- `task-cli plan` - Start interactive task planning
- `task-cli config` - Show current configuration
- `task-cli version` - Show version information

The CLI orchestrates:
1. Loading configuration
2. Running the Q&A conversation
3. Generating the task plan
4. Formatting and outputting the result
"""

from enum import Enum
from typing import Annotated, Optional

import anthropic
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from . import __version__
from .config import get_settings
from .conversation import ConversationError, ConversationManager
from .formatters import format_as_json, format_as_markdown
from .storage import save_plan, load_plan, list_plans


# ============================================================================
# Error Handling Helper
# ============================================================================
# LEARNING NOTE:
# Good error handling transforms cryptic errors into actionable messages.
# We catch specific exception types and provide helpful guidance.

def handle_api_error(error: Exception, console: Console) -> None:
    """
    Handle Anthropic API errors with user-friendly messages.

    LEARNING NOTE:
    The Anthropic SDK raises different exception types for different errors.
    By catching these specifically, we can give targeted advice.

    Args:
        error: The exception that was raised
        console: Rich console for formatted output
    """
    if isinstance(error, anthropic.AuthenticationError):
        console.print(Panel(
            "[red bold]Authentication Error[/red bold]\n\n"
            "Your API key is invalid or has been revoked.\n\n"
            "[dim]To fix:[/dim]\n"
            "1. Check your API key at https://console.anthropic.com/settings/keys\n"
            "2. Update TASK_CLI_ANTHROPIC_API_KEY in your .env file",
            border_style="red"
        ))

    elif isinstance(error, anthropic.RateLimitError):
        console.print(Panel(
            "[yellow bold]Rate Limited[/yellow bold]\n\n"
            "You've made too many requests. Please wait a moment.\n\n"
            "[dim]The API has request limits to ensure fair usage.[/dim]",
            border_style="yellow"
        ))

    elif isinstance(error, anthropic.BadRequestError):
        # Check for specific error messages
        error_msg = str(error)

        if "credit balance" in error_msg.lower() or "billing" in error_msg.lower():
            console.print(Panel(
                "[red bold]Billing Error[/red bold]\n\n"
                "Your Anthropic account needs credits to use the API.\n\n"
                "[dim]To fix:[/dim]\n"
                "1. Visit https://console.anthropic.com/settings/billing\n"
                "2. Add credits or upgrade your plan\n"
                "3. Try again once your account has credits",
                border_style="red"
            ))
        else:
            console.print(Panel(
                f"[red bold]Invalid Request[/red bold]\n\n"
                f"{error_msg}\n\n"
                "[dim]This might be a bug in the CLI. Please report it.[/dim]",
                border_style="red"
            ))

    elif isinstance(error, anthropic.APIConnectionError):
        console.print(Panel(
            "[red bold]Connection Error[/red bold]\n\n"
            "Could not connect to the Anthropic API.\n\n"
            "[dim]To fix:[/dim]\n"
            "1. Check your internet connection\n"
            "2. Try again in a few moments\n"
            "3. Check https://status.anthropic.com for API status",
            border_style="red"
        ))

    elif isinstance(error, anthropic.APIStatusError):
        console.print(Panel(
            f"[red bold]API Error ({error.status_code})[/red bold]\n\n"
            f"{error.message}\n\n"
            "[dim]This is an issue with the Anthropic API. Try again later.[/dim]",
            border_style="red"
        ))

    else:
        # Unknown error - show the raw message
        console.print(f"[red bold]Unexpected Error:[/red bold] {error}")


# ============================================================================
# Create the Typer App
# ============================================================================
# This is the main application object. Commands are added with @app.command()

app = typer.Typer(
    name="task-cli",
    help="AI-powered task planning assistant. Describe your task and get a structured plan.",
    add_completion=False,  # Disable shell completion (simplifies installation)
    no_args_is_help=True,  # Show help if no command is given
)

# Rich console for beautiful terminal output
# All output goes through this for consistent formatting
console = Console()


# ============================================================================
# Output Format Enum
# ============================================================================

class OutputFormat(str, Enum):
    """
    Supported output formats for task plans.

    LEARNING NOTE:
    This is a str Enum (inherits from both str and Enum).
    Typer uses this to create a --format flag with choices.
    """
    MARKDOWN = "markdown"
    JSON = "json"


# ============================================================================
# Main Command: plan
# ============================================================================

@app.command()
def plan(
    # === Positional Argument ===
    task: Annotated[
        Optional[str],
        typer.Argument(
            help="Initial task description. If not provided, you'll be prompted."
        )
    ] = None,

    # === Options (flags) ===
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--format", "-f",
            help="Output format for the generated plan."
        )
    ] = OutputFormat.MARKDOWN,

    output_file: Annotated[
        Optional[str],
        typer.Option(
            "--output", "-o",
            help="Write output to file instead of stdout."
        )
    ] = None,

    max_questions: Annotated[
        int,
        typer.Option(
            "--max-questions", "-q",
            help="Maximum clarifying questions to ask.",
            min=1,
            max=10
        )
    ] = 5,

    skip_questions: Annotated[
        bool,
        typer.Option(
            "--skip-questions", "-s",
            help="Skip clarifying questions and generate plan immediately."
        )
    ] = False,

    save: Annotated[
        bool,
        typer.Option(
            "--save",
            help="Save the plan to ~/.task-cli/plans/ after generating."
        )
    ] = False,
) -> None:
    """
    Create a structured task plan through an AI-powered conversation.

    The assistant will ask clarifying questions to understand your task,
    then generate a detailed, actionable plan.

    \b
    Examples:
        # Interactive mode - prompts for task description
        task-cli plan

        # Provide task directly
        task-cli plan "Build a REST API for user management"

        # JSON output to file
        task-cli plan -f json -o plan.json "Migrate the database"

        # Skip questions for simple tasks
        task-cli plan -s "Write unit tests for login"
    """
    # -------------------------------------------------------------------------
    # Step 1: Validate Configuration
    # -------------------------------------------------------------------------
    try:
        settings = get_settings()
    except Exception as e:
        console.print(
            f"[red bold]Configuration Error:[/red bold] {e}\n\n"
            "Make sure TASK_CLI_ANTHROPIC_API_KEY is set in your environment or .env file.\n"
            "See .env.example for the required format."
        )
        raise typer.Exit(1)

    # -------------------------------------------------------------------------
    # Step 2: Get Task Description
    # -------------------------------------------------------------------------
    if task is None:
        # No task provided - show welcome and prompt for it
        console.print(Panel(
            "[bold]Welcome to the Task Planning Assistant![/bold]\n\n"
            "Describe your task and I'll help you break it down into\n"
            "actionable steps through a short conversation.",
            title="Task CLI",
            border_style="blue"
        ))
        task = Prompt.ask("\n[bold cyan]What task would you like to plan?[/bold cyan]")

    # Validate we have something to work with
    if not task.strip():
        console.print("[red]Error:[/red] Task description cannot be empty.")
        raise typer.Exit(1)

    # -------------------------------------------------------------------------
    # Step 3: Initialize Conversation
    # -------------------------------------------------------------------------
    try:
        manager = ConversationManager()
    except Exception as e:
        console.print(f"[red]Failed to initialize:[/red] {e}")
        raise typer.Exit(1)

    # Override max questions if user specified a different value
    if max_questions != settings.max_questions:
        manager.settings = get_settings()
        # Note: In a more robust implementation, we'd pass this as a parameter

    console.print(f"\n[dim]Planning task:[/dim] {task}\n")

    # -------------------------------------------------------------------------
    # Step 4: Run Conversation (or skip it)
    # -------------------------------------------------------------------------
    # LEARNING NOTE:
    # We wrap API calls in try/except to catch and handle errors gracefully.
    # This prevents ugly tracebacks and gives users actionable feedback.

    try:
        if skip_questions:
            # Quick mode: go straight to plan generation
            console.print("[yellow]Skipping questions, generating plan directly...[/yellow]\n")
            manager.start(task)
            manager.is_ready = True
        else:
            # Interactive mode: conduct the Q&A conversation
            questions = manager.start(task)

            # Loop until Claude is ready (no more questions)
            while questions and not manager.is_ready:
                for question in questions:
                    # Display the question in a nice panel
                    console.print(Panel(
                        question.question,
                        title="Question",
                        border_style="cyan"
                    ))

                    # Show context if provided (why we're asking)
                    if question.context:
                        console.print(f"[dim]({question.context})[/dim]")

                    # Show suggestions if provided
                    if question.suggestions:
                        suggestions = " | ".join(question.suggestions)
                        console.print(f"[dim]Suggestions: {suggestions}[/dim]")

                    # Get the user's answer
                    answer = Prompt.ask("\n[bold]Your answer[/bold]")

                    # Send to Claude and get next questions
                    questions = manager.answer(answer)

            console.print("\n[green]Great! Generating your task plan...[/green]\n")

    except (anthropic.APIError, anthropic.APIConnectionError) as e:
        # Handle API errors with user-friendly messages
        handle_api_error(e, console)
        raise typer.Exit(1)

    except KeyboardInterrupt:
        # User pressed Ctrl+C
        console.print("\n[yellow]Cancelled by user.[/yellow]")
        raise typer.Exit(130)  # Standard exit code for SIGINT

    # -------------------------------------------------------------------------
    # Step 5: Generate the Plan
    # -------------------------------------------------------------------------
    try:
        task_plan = manager.generate_plan()

    except (anthropic.APIError, anthropic.APIConnectionError) as e:
        handle_api_error(e, console)
        raise typer.Exit(1)

    except ConversationError as e:
        console.print(f"[red]Error generating plan:[/red] {e}")
        raise typer.Exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user.[/yellow]")
        raise typer.Exit(130)

    # -------------------------------------------------------------------------
    # Step 6: Format Output
    # -------------------------------------------------------------------------
    if output_format == OutputFormat.JSON:
        output = format_as_json(task_plan)
    else:
        output = format_as_markdown(task_plan)

    # -------------------------------------------------------------------------
    # Step 7: Write or Display Output
    # -------------------------------------------------------------------------
    if output_file:
        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
        console.print(f"[green]Plan saved to:[/green] {output_file}")
    else:
        # Display in terminal
        if output_format == OutputFormat.MARKDOWN:
            # Rich can render Markdown beautifully in the terminal
            console.print(Markdown(output))
        else:
            # JSON is already formatted, print as-is
            console.print(output)

    # -------------------------------------------------------------------------
    # Step 8: Save Plan (if requested)
    # -------------------------------------------------------------------------
    # ARCHITECTURE NOTE:
    # main.py doesn't know HOW to save - it just calls storage.save_plan()
    # This keeps main.py focused on CLI orchestration, not file operations.

    should_save = save  # True if --save flag was used

    # If no --save flag, ask the user
    if not should_save and not output_file:
        # Only ask if we didn't already write to a file
        from rich.prompt import Confirm
        should_save = Confirm.ask("\n[bold]Save this plan to ~/.task-cli/plans/?[/bold]")

    if should_save:
        try:
            saved_path = save_plan(task_plan)
            console.print(f"\n[green]Plan saved![/green]")
            console.print(f"  JSON: {saved_path}.json")
            console.print(f"  Markdown: {saved_path}.md")
        except Exception as e:
            console.print(f"[red]Failed to save plan:[/red] {e}")


# ============================================================================
# Utility Commands
# ============================================================================

@app.command()
def config() -> None:
    """Show current configuration (API key is masked)."""
    try:
        settings = get_settings()
        console.print(Panel(
            f"[bold]Model:[/bold] {settings.model_name}\n"
            f"[bold]Max Tokens:[/bold] {settings.max_tokens}\n"
            f"[bold]Max Questions:[/bold] {settings.max_questions}\n"
            f"[bold]API Key:[/bold] {'*' * 20}... [green](set)[/green]",
            title="Current Configuration",
            border_style="green"
        ))
    except Exception as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"[bold]task-cli[/bold] version {__version__}")


# ============================================================================
# Plan Storage Commands
# ============================================================================
# ARCHITECTURE NOTE:
# These commands use storage.py for all file operations.
# main.py handles user interaction, storage.py handles persistence.

@app.command(name="list")
def list_saved_plans() -> None:
    """List all saved plans in ~/.task-cli/plans/"""
    from rich.table import Table

    plans = list_plans()

    if not plans:
        console.print("[yellow]No saved plans found.[/yellow]")
        console.print("[dim]Create a plan with: task-cli plan \"your task\"[/dim]")
        return

    # Display as a table
    table = Table(title="Saved Plans")
    table.add_column("Date", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Filename", style="dim")

    for plan in plans:
        # Extract date from filename (first 10 chars: 2026-01-07)
        date = plan["filename"][:10] if len(plan["filename"]) > 10 else "Unknown"
        table.add_row(date, plan["title"], plan["filename"])

    console.print(table)
    console.print(f"\n[dim]Load a plan with: task-cli load <filename>[/dim]")


@app.command()
def load(
    filename: Annotated[
        str,
        typer.Argument(help="Filename of the plan to load (without .json)")
    ],
    output_format: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.MARKDOWN,
) -> None:
    """Load and display a saved plan."""
    try:
        task_plan = load_plan(filename)

        # Format and display
        if output_format == OutputFormat.JSON:
            console.print(format_as_json(task_plan))
        else:
            console.print(Markdown(format_as_markdown(task_plan)))

    except FileNotFoundError:
        console.print(f"[red]Plan not found:[/red] {filename}")
        console.print("[dim]Use 'task-cli list' to see available plans.[/dim]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error loading plan:[/red] {e}")
        raise typer.Exit(1)


# ============================================================================
# Entry Point
# ============================================================================
# This allows running the module directly: python -m contextual_task_cli.main

if __name__ == "__main__":
    app()
