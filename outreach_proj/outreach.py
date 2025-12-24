"""
Main outreach orchestration module.

This module coordinates email generation and sending for all contacts.
"""

import csv
import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from io import StringIO
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

# Handle both direct script execution and package import
if __name__ == "__main__" or __package__ is None or __package__ == "":
    # Running as a script - add parent directory to path
    _parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _parent_dir not in sys.path:
        sys.path.insert(0, _parent_dir)
    from outreach_proj.generate_email import generate_personalized_email
    from outreach_proj.send_email import get_gmail_service, create_message, send_message
else:
    # Running as part of package
    from .generate_email import generate_personalized_email
    from .send_email import get_gmail_service, create_message, send_message

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Console for rich output
console = Console()

# Default paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DEFAULT_CONTACTS_FILE = os.path.join(BASE_DIR, "contacts.csv")
DEFAULT_LOG_FILE = os.path.join(BASE_DIR, "logs.csv")
DEFAULT_DRAFTS_DIR = os.path.join(BASE_DIR, "drafts")


def load_config(config_file: str | None = None) -> dict[str, Any]:
    """Load configuration from JSON file."""
    path = config_file or DEFAULT_CONFIG_FILE
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_contacts(contacts_file: str | None = None) -> list[dict[str, str]]:
    """Load contacts from CSV file."""
    path = contacts_file or DEFAULT_CONTACTS_FILE
    with open(path, newline="", encoding="utf-8") as f:
        content = f.read()
        # Handle BOM from Excel-exported CSVs
        if content.startswith("\ufeff"):
            content = content[1:]
        reader = csv.DictReader(StringIO(content))
        return list(reader)


def load_contacted_emails(log_file: str | None = None) -> set[str]:
    """
    Load set of already-contacted email addresses from the log file.
    
    Returns emails with SENT or DRY_RUN status to avoid re-processing.
    """
    path = log_file or DEFAULT_LOG_FILE
    contacted = set()
    
    if not os.path.exists(path):
        return contacted
    
    try:
        with open(path, newline="", encoding="utf-8") as f:
            content = f.read()
            # Handle BOM if present
            if content.startswith("\ufeff"):
                content = content[1:]
            reader = csv.DictReader(StringIO(content))
            for row in reader:
                status = (row.get("Status") or "").strip().upper()
                email = (row.get("Email") or "").strip().lower()
                # Only skip contacts that were successfully processed
                if status in ("SENT", "DRY_RUN") and email:
                    contacted.add(email)
    except Exception as e:
        logger.warning(f"Could not read log file: {e}")
    
    return contacted


def append_log(
    contact: dict[str, str],
    status: str,
    subject: str,
    error_msg: str = "",
    log_file: str | None = None,
) -> None:
    """Append an entry to the log file."""
    path = log_file or DEFAULT_LOG_FILE
    file_exists = os.path.exists(path)
    
    with open(path, "a", newline="", encoding="utf-8") as f:
        fieldnames = ["Timestamp", "Email", "Company", "Status", "Subject", "Error"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "Timestamp": datetime.now().isoformat(),
            "Email": contact.get("Email Address", ""),
            "Company": contact.get("Company", ""),
            "Status": status,
            "Subject": subject,
            "Error": error_msg,
        })


def save_draft(
    contact: dict[str, str],
    subject: str,
    body: str,
    drafts_dir: str | None = None,
) -> str:
    """Save email draft to a text file for review."""
    path = drafts_dir or DEFAULT_DRAFTS_DIR
    
    if not os.path.exists(path):
        os.makedirs(path)

    # Create safe filename
    first = contact.get("First Name", "Unknown").replace(" ", "_")
    last = contact.get("Last Name", "Unknown").replace(" ", "_")
    comp = contact.get("Company", "Company").replace(" ", "_")
    filename = f"{first}_{last}_{comp}.txt"
    filepath = os.path.join(path, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"TO: {contact.get('Email Address')}\n")
        f.write(f"SUBJECT: {subject}\n")
        f.write("-" * 40 + "\n\n")
        f.write(body)

    return filename


def run(
    dry_run: bool = True,
    contacts_file: str | None = None,
    config_file: str | None = None,
    limit: int | None = None,
) -> None:
    """
    Run the outreach campaign.
    
    Args:
        dry_run: If True, save drafts instead of sending.
        contacts_file: Path to contacts CSV (uses default if None).
        config_file: Path to config JSON (uses default if None).
        limit: Maximum number of emails to process.
    """
    config = load_config(config_file)
    contacts = load_contacts(contacts_file)
    
    # Filter out contacts without email
    contacts = [c for c in contacts if c.get("Email Address", "").strip()]
    
    # Load already-contacted emails and filter them out
    already_contacted = load_contacted_emails()
    original_count = len(contacts)
    contacts = [
        c for c in contacts 
        if c.get("Email Address", "").strip().lower() not in already_contacted
    ]
    skipped_count = original_count - len(contacts)
    
    if skipped_count > 0:
        console.print(f"[dim]Skipping {skipped_count} already-contacted email(s)[/dim]")
    
    # Apply limit
    if limit:
        contacts = contacts[:limit]
    
    if not contacts:
        console.print("[yellow]No new contacts to process.[/yellow]")
        return
    
    # Get Gmail service if sending
    service = None
    if not dry_run:
        console.print("[blue]Authenticating with Gmail...[/blue]")
        service = get_gmail_service()
    
    # Process contacts with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing contacts...", total=len(contacts))
        
        for contact in contacts:
            email = contact.get("Email Address", "").strip()
            first_name = contact.get("First Name", "there")
            company = contact.get("Company", "Unknown")
            
            progress.update(task, description=f"[cyan]{first_name}[/cyan] @ {company}")
            
            try:
                subject, body = generate_personalized_email(contact, config)
                
                if dry_run:
                    filename = save_draft(contact, subject, body)
                    console.print(f"  [dim]→ Draft:[/dim] drafts/{filename}")
                    append_log(contact, "DRY_RUN", subject)
                else:
                    msg = create_message(
                        sender_name=config["your_name"],
                        sender_email=config["your_email"],
                        to=email,
                        subject=subject,
                        body_text=body,
                    )
                    send_message(service, "me", msg)
                    append_log(contact, "SENT", subject)
                    console.print(f"  [green]✓ Sent to {email}[/green]")
                    
                    # Random delay to avoid spam filters
                    delay = random.randint(15, 45)
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Failed for {email}: {e}")
                append_log(contact, "ERROR", "N/A", str(e))
                console.print(f"  [red]✗ Error: {e}[/red]")
            
            progress.advance(task)


# Keep main() for backwards compatibility with direct script execution
def main() -> None:
    """Legacy entry point for direct script execution."""
    run(dry_run=True)


if __name__ == "__main__":
    main()