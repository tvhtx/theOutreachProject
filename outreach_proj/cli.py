"""
Command-line interface for the outreach project.

Usage:
    outreach --dry-run          Preview emails as drafts
    outreach --send             Send emails for real
    outreach --help             Show help
"""

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

console = Console()


@click.command()
@click.option(
    "--dry-run/--send",
    default=True,
    help="Dry run saves drafts to files. --send actually sends emails.",
)
@click.option(
    "--contacts",
    type=click.Path(exists=True),
    default=None,
    help="Path to contacts CSV file. Defaults to contacts.csv in package.",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    default=None,
    help="Path to config.json file. Defaults to config.json in package.",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Limit number of emails to process.",
)
def main(dry_run: bool, contacts: str | None, config: str | None, limit: int | None) -> None:
    """
    Outreach - Automated personalized email outreach.
    
    Generate and send personalized networking emails using AI.
    """
    from . import outreach
    
    mode = "DRY RUN" if dry_run else "SENDING"
    style = "yellow" if dry_run else "red bold"
    
    console.print(Panel(
        f"[{style}]Mode: {mode}[/{style}]\n"
        f"Contacts: {contacts or 'default'}\n"
        f"Limit: {limit or 'all'}",
        title="🚀 Outreach Starting",
        border_style="blue",
    ))
    
    if not dry_run:
        if not click.confirm("⚠️  This will send REAL emails. Continue?"):
            console.print("[yellow]Aborted.[/yellow]")
            return
    
    try:
        outreach.run(
            dry_run=dry_run,
            contacts_file=contacts,
            config_file=config,
            limit=limit,
        )
        console.print("\n[green]✓ Outreach complete![/green]")
    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()


if __name__ == "__main__":
    main()
