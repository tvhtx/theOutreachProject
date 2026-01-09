# Outreach Project

**AI-Powered Personalized Email Outreach Platform**

A multi-tenant SaaS application for sending personalized networking emails using AI (GPT-4) for content generation and Gmail API for delivery. Features a modern web dashboard for managing contacts, campaigns, templates, and drafts.

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)]()
[![License](https://img.shields.io/badge/license-MIT-purple.svg)]()

## ✨ Features

### Core Functionality
- 🤖 **AI-Powered Emails** - GPT-4 generates personalized, contextual emails
- 📧 **Gmail Integration** - Send directly via Gmail API
- 🎨 **Modern Dashboard** - Beautiful web interface with real-time updates
- 📝 **Draft System** - Preview and edit emails before sending
- 📊 **Activity Logging** - Track all email activity

### Multi-Tenant SaaS (v2.0)
- 🔐 **User Authentication** - JWT-based login and registration
- 👤 **User Profiles** - Customizable sender information
- 📚 **Template Library** - Reusable email templates
- 🗄️ **Database Storage** - SQLite/PostgreSQL support
- 🔒 **Data Isolation** - Each user sees only their data

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Install package with all dependencies
pip install -e .
```

### 2. Configure Environment

```bash
# Copy example env file
cp outreach_proj/.env.example outreach_proj/.env

# Edit with your settings
nano outreach_proj/.env
```

**Required settings:**
- `OPENAI_API_KEY` - Your OpenAI API key
- `SECRET_KEY` - Random string for JWT tokens (production)

### 3. Set Up Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download as `credentials.json` to `outreach_proj/`

### 4. Run the Application

```bash
# Terminal 1: Start the API server
python api_server.py

# Terminal 2: Start the frontend server
python serve.py
```

Open http://localhost:8080/frontend/ in your browser.

**New user?** Go to http://localhost:8080/frontend/register.html to create an account.

## 📁 Project Structure

```
theOutreachProject/
├── api_server.py               # Flask API backend (v2.0)
├── serve.py                    # Frontend HTTP server
├── frontend/
│   ├── index.html              # Main dashboard
│   ├── login.html              # Login page
│   ├── register.html           # Registration page
│   ├── styles.css              # Styling
│   └── app.js                  # Frontend logic with auth
├── outreach_proj/
│   ├── __init__.py
│   ├── config.py               # Environment-based configuration
│   ├── database.py             # SQLAlchemy database setup
│   ├── models.py               # Database models (User, Contact, etc.)
│   ├── auth.py                 # JWT authentication
│   ├── cli.py                  # Command-line interface
│   ├── outreach.py             # Legacy orchestration (file-based)
│   ├── generate_email.py       # OpenAI email generation
│   ├── send_email.py           # Gmail API integration
│   └── services/
│       ├── contact_service.py  # Contact CRUD operations
│       ├── template_service.py # Template management
│       └── email_service.py    # Email sending service
├── tests/
│   └── test_outreach.py        # Unit tests
├── pyproject.toml              # Project dependencies
└── README.md
```

## 🔌 API Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create new account |
| POST | `/api/auth/login` | Login & get JWT token |
| GET | `/api/auth/me` | Get current user [Auth] |
| PUT | `/api/auth/profile` | Update profile [Auth] |

### Contacts (v2 - Database)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v2/contacts` | List contacts [Auth] |
| POST | `/api/v2/contacts` | Create contact [Auth] |
| GET | `/api/v2/contacts/<id>` | Get contact [Auth] |
| PUT | `/api/v2/contacts/<id>` | Update contact [Auth] |
| DELETE | `/api/v2/contacts/<id>` | Delete contact [Auth] |
| POST | `/api/v2/contacts/import` | Bulk import [Auth] |

### Templates (v2 - Database)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v2/templates` | List templates [Auth] |
| GET | `/api/v2/templates/<id>` | Get template [Auth] |

### Legacy Endpoints (File-based)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/contacts` | Get contacts (CSV) |
| GET | `/api/config` | Get config |
| POST | `/api/config` | Save config |
| GET | `/api/logs` | Get email logs |
| POST | `/api/dry-run` | Generate drafts |
| POST | `/api/send` | Send emails |
| GET | `/api/drafts` | Get saved drafts |

## 🔧 Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-your-key-here

# Authentication
SECRET_KEY=your-random-secret-key-for-jwt
JWT_EXPIRATION_HOURS=24

# Database
DATABASE_URL=sqlite:///outreach.db
# Or: DATABASE_URL=postgresql://user:pass@host/db

# Server
API_HOST=127.0.0.1
API_PORT=5000
FLASK_DEBUG=false

# CORS
ALLOWED_ORIGINS=http://localhost:8080,https://yourdomain.com

# Rate Limiting
RATE_LIMIT_WINDOW=60
RATE_LIMIT_MAX_REQUESTS=30

# Email Settings
MAX_EMAILS_PER_REQUEST=50
EMAIL_DELAY_MIN_SECONDS=15
EMAIL_DELAY_MAX_SECONDS=45
```

### User Profile Configuration

Users can configure their profile in Settings:
- Full name
- Email signature components
- School/Organization
- Major/Department
- Custom pitch and goals

## 🧪 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linting
ruff check .

# Format code
black .

# Type checking
mypy outreach_proj
```

## 🐳 Deployment (Coming Soon)

```bash
# Build Docker image
docker build -t outreach .

# Run with Docker Compose
docker-compose up -d
```

## 📝 CLI Usage

```bash
# Preview drafts (dry run)
outreach --dry-run

# Send emails for real
outreach --send

# Limit number of emails
outreach --limit 5

# Use custom files
outreach --contacts path/to/contacts.csv --config path/to/config.json
```

## 🔒 Security Notes

- JWT tokens expire after 24 hours (configurable)
- Passwords are hashed with bcrypt
- All v2 API endpoints require authentication
- Rate limiting prevents abuse
- CORS is configured for allowed origins only
- Debug mode is disabled by default

## 📄 License

MIT License - See LICENSE for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

Built with ❤️ by Taylor Van Horn
