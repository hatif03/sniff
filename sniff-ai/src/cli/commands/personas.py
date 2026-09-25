"""sniff personas command - Manage user behavior profiles."""

from pathlib import Path
from typing import Optional

import questionary
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ...core.persona import PersonaProfile, create_default_personas
from ...core.config import get_config

console = Console()
app = typer.Typer()


@app.command("add")
def add_persona(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Persona identifier"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Interactive mode"),
):
    """Add a new user persona with LLM-assisted structuring."""

    console.print(Panel.fit(
        "[bold cyan]Create New Persona[/bold cyan]\n"
        "Define a user behavior profile for testing.",
        border_style="cyan"
    ))

    config = get_config()
    personas_dir = Path(config.personas_path)

    # Interactive persona creation
    if not name:
        name = questionary.text(
            "Persona identifier (e.g., 'power_user'):",
            validate=lambda x: len(x) > 0 and x.replace('_', '').isalnum()
        ).ask()

    # Check if persona already exists
    persona_path = personas_dir / f"{name}.json"
    if persona_path.exists():
        console.print(f"[yellow]Warning:[/yellow] Persona '{name}' already exists.")
        overwrite = questionary.confirm("Overwrite?", default=False).ask()
        if not overwrite:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0)

    # Gather persona details
    display_name = questionary.text(
        "Display name:",
        default=name.replace('_', ' ').title()
    ).ask()

    description = questionary.text(
        "Description (what makes this persona unique?):",
    ).ask()

    # Behavioral parameters
    console.print("\n[bold]Behavioral Parameters[/bold] (0.0 = Low, 1.0 = High)")

    patience_level = float(questionary.select(
        "Patience level:",
        choices=[
            questionary.Choice("Low (0.2)", 0.2),
            questionary.Choice("Medium (0.5)", 0.5),
            questionary.Choice("High (0.8)", 0.8),
        ]
    ).ask())

    technical_proficiency = float(questionary.select(
        "Technical proficiency:",
        choices=[
            questionary.Choice("Beginner (0.2)", 0.2),
            questionary.Choice("Intermediate (0.5)", 0.5),
            questionary.Choice("Expert (0.8)", 0.8),
        ]
    ).ask())

    exploration_tendency = float(questionary.select(
        "Exploration tendency:",
        choices=[
            questionary.Choice("Focused (0.2)", 0.2),
            questionary.Choice("Balanced (0.5)", 0.5),
            questionary.Choice("Exploratory (0.8)", 0.8),
        ]
    ).ask())

    attention_to_detail = float(questionary.select(
        "Attention to detail:",
        choices=[
            questionary.Choice("Skims quickly (0.2)", 0.2),
            questionary.Choice("Moderate (0.5)", 0.5),
            questionary.Choice("Reads everything (0.8)", 0.8),
        ]
    ).ask())

    # Behavioral guidelines
    console.print("\n[bold]Behavioral Guidelines[/bold]")
    console.print("Enter specific behaviors (one per line, empty line to finish):")

    behavioral_guidelines = []
    while True:
        guideline = questionary.text("Guideline:").ask()
        if not guideline:
            break
        behavioral_guidelines.append(guideline)

    # Default goal template (optional)
    has_default_goal = questionary.confirm(
        "\nAdd default goal template for this persona?",
        default=False
    ).ask()

    default_goal_template = None
    if has_default_goal:
        default_goal_template = questionary.text(
            "Default goal template:"
        ).ask()

    # Tags
    tags_str = questionary.text(
        "\nTags (comma-separated, optional):",
        default=""
    ).ask()

    tags = [t.strip() for t in tags_str.split(',') if t.strip()] if tags_str else []

    # Create persona
    persona = PersonaProfile(
        name=name,
        display_name=display_name,
        description=description,
        patience_level=patience_level,
        technical_proficiency=technical_proficiency,
        exploration_tendency=exploration_tendency,
        attention_to_detail=attention_to_detail,
        behavioral_guidelines=behavioral_guidelines,
        default_goal_template=default_goal_template,
        tags=tags
    )

    # Preview
    console.print("\n[bold]Persona Preview:[/bold]")
    console.print(Panel(persona.to_prompt_context(), border_style="green"))

    # Confirm and save
    confirm = questionary.confirm("\nSave this persona?", default=True).ask()

    if confirm:
        persona.save(personas_dir)
        console.print(f"[green]✓[/green] Saved persona to {persona_path}")
    else:
        console.print("[yellow]Cancelled.[/yellow]")


@app.command("list")
def list_personas(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full details")
):
    """List all available personas."""

    config = get_config()
    personas_dir = Path(config.personas_path)

    # Create default personas if directory is empty
    if not personas_dir.exists() or not list(personas_dir.glob('*.json')):
        console.print("[yellow]No personas found. Creating defaults...[/yellow]")
        create_default_personas(personas_dir)

    persona_names = PersonaProfile.list_available(personas_dir)

    if not persona_names:
        console.print("[yellow]No personas found.[/yellow]")
        console.print("Create one with: [cyan]sniff personas add[/cyan]")
        return

    if verbose:
        # Show detailed view
        for name in persona_names:
            try:
                persona = PersonaProfile.load(name, personas_dir)
                console.print(f"\n[bold cyan]{persona.display_name}[/bold cyan] ({name})")
                console.print(Panel(persona.to_prompt_context(), border_style="cyan"))
            except Exception as e:
                console.print(f"[red]Error loading {name}:[/red] {e}")
    else:
        # Show table view
        table = Table(title="Available Personas", show_header=True)
        table.add_column("Name", style="cyan")
        table.add_column("Display Name", style="white")
        table.add_column("Patience", justify="center")
        table.add_column("Technical", justify="center")
        table.add_column("Tags", style="dim")

        for name in persona_names:
            try:
                persona = PersonaProfile.load(name, personas_dir)
                table.add_row(
                    persona.name,
                    persona.display_name,
                    f"{persona.patience_level:.1f}",
                    f"{persona.technical_proficiency:.1f}",
                    ", ".join(persona.tags[:3]) if persona.tags else ""
                )
            except Exception as e:
                table.add_row(name, f"[red]Error: {e}[/red]", "", "", "")

        console.print(table)
        console.print("\nUse [cyan]--verbose[/cyan] for full details")


@app.command("show")
def show_persona(
    name: str = typer.Argument(..., help="Persona name to display")
):
    """Show detailed information about a specific persona."""

    config = get_config()
    personas_dir = Path(config.personas_path)

    try:
        persona = PersonaProfile.load(name, personas_dir)
        console.print(f"\n[bold cyan]{persona.display_name}[/bold cyan]")
        console.print(Panel(persona.to_prompt_context(), border_style="cyan"))

        # Show raw JSON path
        console.print(f"\n[dim]Stored at: {personas_dir / f'{name}.json'}[/dim]")

    except FileNotFoundError:
        console.print(f"[red]Error:[/red] Persona '{name}' not found.")
        console.print("Available personas:")
        available = PersonaProfile.list_available(personas_dir)
        for available_name in available:
            console.print(f"  - {available_name}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error loading persona:[/red] {e}")
        raise typer.Exit(1)


@app.command("test")
def test_persona(
    name: str = typer.Argument(..., help="Persona name to test"),
    goal: str = typer.Option(None, "--goal", "-g", help="Test goal")
):
    """Test persona prompt context generation."""

    config = get_config()
    personas_dir = Path(config.personas_path)

    try:
        persona = PersonaProfile.load(name, personas_dir)

        console.print(Panel.fit(
            f"[bold]Testing Persona: {persona.display_name}[/bold]",
            border_style="cyan"
        ))

        # Show prompt context
        console.print("\n[bold]Prompt Context:[/bold]")
        console.print(Panel(persona.to_prompt_context(), border_style="green"))

        # If goal provided, show combined context
        if goal:
            console.print("\n[bold]Combined Context with Goal:[/bold]")
            combined = f"{persona.to_prompt_context()}\n\nGoal: {goal}"
            console.print(Panel(combined, border_style="blue"))

        # Show as JSON
        if questionary.confirm("\nShow raw JSON?", default=False).ask():
            console.print("\n[bold]Raw JSON:[/bold]")
            console.print(persona.model_dump_json(indent=2))

    except FileNotFoundError:
        console.print(f"[red]Error:[/red] Persona '{name}' not found.")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
