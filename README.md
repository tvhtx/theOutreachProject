# Outreach Project

Automated personalized email outreach system using OpenAI for content generation and Gmail API for delivery. Features a modern web dashboard for managing contacts, campaigns, and drafts.

## Features

- 🤖 AI-powered personalized email generation using GPT-4
- 📧 Gmail API integration for sending emails
- 🎨 Modern web dashboard with real-time updates
- 📝 Dry-run mode to preview/edit drafts before sending
- 📊 CSV-based contact management with import/export
- 📋 Comprehensive logging of all email activity
- 🔒 API authentication and rate limiting
- ✏️ Draft editing before sending

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

# Install Flask and CORS
pip install flask flask-cors
```

### 2. Configure Environment

```bash
# Copy example env file
cp outreach_proj/.env.example outreach_proj/.env

# Edit with your OpenAI API key
# OPENAI_API_KEY=sk-your-key-here
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

### 5. Running the Application

**Option A: Web Dashboard (Recommended)**

```bash
# Terminal 1: Start the API server
python api_server.py

# Terminal 2: Start the frontend server
python serve.py
```

Then open http://localhost:8080/frontend/ in your browser.

**Option B: Command Line**

```bash
# Preview drafts (dry run - default)
outreach --dry-run

# Send emails for real
outreach --send

# Limit number of emails
outreach --limit 5
```

## Project Structure

```
theOutreachProject/
├── api_server.py           # Flask API backend
├── serve.py                # Simple HTTP server for frontend
├── frontend/
│   ├── index.html          # Dashboard HTML
│   ├── styles.css          # Styling
│   └── app.js              # Frontend logic
├── outreach_proj/
│   ├── __init__.py
│   ├── cli.py              # Command-line interface
│   ├── outreach.py         # Main orchestration
│   ├── generate_email.py   # OpenAI integration
│   ├── send_email.py       # Gmail API integration
│   ├── prompt_components.py # Email templates
│   ├── config.json         # Your personal info
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
  "your_phone": "(555) 123-4567",
  "your_school": "Your University",
  "your_major": "Your Major",
  "graduation_year": "2027",
  "your_title": "Your Title/Role",
  "your_department": "Your Department",
  "your_pitch": "Brief intro about yourself",
  "target_goal": "What you're looking for"
}
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/contacts` | Get all contacts |
| POST | `/api/contacts` | Add new contact |
| DELETE | `/api/contacts/<email>` | Delete contact |
| GET | `/api/config` | Get configuration |
| POST | `/api/config` | Save configuration |
| GET | `/api/logs` | Get email logs |
| POST | `/api/dry-run` | Generate drafts |
| POST | `/api/send` | Send emails |
| GET | `/api/drafts` | Get saved drafts |

## Security

For production use, set these environment variables:

```bash
# Optional API key for authentication
API_KEY=your-secret-api-key

# Restrict CORS origins
ALLOWED_ORIGINS=https://yourdomain.com

# Disable debug mode
FLASK_DEBUG=false
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run linting
ruff check .

# Format code
black .

# Type checking
mypy outreach_proj
```

## License

MIT
