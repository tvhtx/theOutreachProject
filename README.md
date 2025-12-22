# Outreach Project

Automated personalized email outreach system using OpenAI for content generation and Gmail API for delivery.

## Features

- 🤖 AI-powered personalized email generation using GPT-4
- 📧 Gmail API integration for sending emails
- 📝 Dry-run mode to preview drafts before sending
- 📊 CSV-based contact management
- 📋 Logging of all sent emails

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Install package
pip install -e .
```

### 2. Configure Environment

```bash
# Copy example env file
cp outreach_proj/.env.example outreach_proj/.env

# Edit with your OpenAI API key
```

### 3. Set Up Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download as `credentials.json` to `outreach_proj/`

### 4. Prepare Contacts

Edit `outreach_proj/contacts.csv` with your contacts:

```csv
First Name,Last Name,Company,Email Address,Job Title
John,Doe,Acme Corp,john@acme.com,Software Engineer
```

### 5. Run

```bash
# Preview drafts (dry run - default)
outreach --dry-run

# Send emails for real
outreach --send

# Use custom contacts file
outreach --contacts path/to/contacts.csv
```

## Project Structure

```
outreach_proj/
├── outreach_proj/
│   ├── __init__.py
│   ├── cli.py              # Command-line interface
│   ├── outreach.py         # Main orchestration
│   ├── generate_email.py   # OpenAI integration
│   ├── send_email.py       # Gmail API integration
│   ├── prompt_components.py # Email templates
│   ├── config.json         # Your info
│   ├── contacts.csv        # Target contacts
│   └── drafts/             # Generated previews
├── pyproject.toml
└── README.md
```

## Configuration

Edit `outreach_proj/config.json`:

```json
{
  "your_name": "Your Name",
  "your_email": "you@gmail.com",
  "your_school": "Your University",
  "your_major": "Your Major",
  "your_pitch": "Brief intro about yourself",
  "target_goal": "What you're looking for"
}
```

## License

MIT
