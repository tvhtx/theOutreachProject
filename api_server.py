#!/usr/bin/env python3
"""
Flask API server for the Outreach frontend.
Provides endpoints for dry run and campaign functionality.
"""

import csv
import json
import os
import sys
import time
import re
from datetime import datetime
from functools import wraps
from io import StringIO
from flask import Flask, jsonify, request, g
from flask_cors import CORS

# Add the project to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from outreach_proj.outreach import (
    load_config,
    load_contacts,
    load_contacted_emails,
    append_log,
    save_draft,
    DEFAULT_CONFIG_FILE,
    DEFAULT_CONTACTS_FILE,
    DEFAULT_LOG_FILE,
    DEFAULT_DRAFTS_DIR,
)
from outreach_proj.generate_email import generate_personalized_email
from outreach_proj.send_email import get_gmail_service, create_message, send_message

app = Flask(__name__)

# CORS Configuration - Restrict to known origins
ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:8080,http://127.0.0.1:8080').split(',')
CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True)

# API Key for authentication (optional but recommended)
API_KEY = os.environ.get('API_KEY', None)

# Rate limiting configuration
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 30  # max requests per window
rate_limit_cache = {}


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def rate_limit():
    """Simple in-memory rate limiter."""
    client_ip = request.remote_addr
    current_time = time.time()
    
    if client_ip not in rate_limit_cache:
        rate_limit_cache[client_ip] = []
    
    # Clean old requests
    rate_limit_cache[client_ip] = [
        t for t in rate_limit_cache[client_ip] 
        if current_time - t < RATE_LIMIT_WINDOW
    ]
    
    if len(rate_limit_cache[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    
    rate_limit_cache[client_ip].append(current_time)
    return True


def require_api_key(f):
    """Decorator to require API key authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip auth if no API key is configured
        if not API_KEY:
            return f(*args, **kwargs)
        
        # Check for API key in header
        provided_key = request.headers.get('X-API-Key')
        if not provided_key or provided_key != API_KEY:
            return jsonify({"error": "Invalid or missing API key"}), 401
        
        return f(*args, **kwargs)
    return decorated_function


@app.before_request
def before_request():
    """Run before each request - rate limiting and logging."""
    # Rate limiting
    if not rate_limit():
        return jsonify({"error": "Rate limit exceeded. Please wait."}), 429
    
    # Log request
    g.start_time = time.time()


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    """Get all contacts."""
    try:
        contacts = load_contacts()
        contacted = load_contacted_emails()
        
        result = []
        for c in contacts:
            email = c.get("Email Address", "").strip().lower()
            status = "pending"
            if not email:
                status = "no-email"
            elif email in contacted:
                status = "sent"
            
            result.append({
                "firstName": c.get("First Name", ""),
                "lastName": c.get("Last Name", ""),
                "email": c.get("Email Address", ""),
                "company": c.get("Company", ""),
                "jobTitle": c.get("Job Title", ""),
                "city": c.get("Business City", ""),
                "state": c.get("Business State", ""),
                "status": status
            })
        
        return jsonify({"contacts": result, "total": len(result)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/contacts', methods=['POST'])
@require_api_key
def add_contact():
    """Add a new contact."""
    try:
        data = request.json or {}
        
        # Validate required fields
        first_name = data.get('firstName', '').strip()
        last_name = data.get('lastName', '').strip()
        
        if not first_name or not last_name:
            return jsonify({"error": "First name and last name are required"}), 400
        
        email = data.get('email', '').strip()
        if email and not validate_email(email):
            return jsonify({"error": "Invalid email format"}), 400
        
        # Load existing contacts
        contacts = load_contacts()
        
        # Check for duplicate email
        if email:
            for c in contacts:
                if c.get("Email Address", "").strip().lower() == email.lower():
                    return jsonify({"error": "A contact with this email already exists"}), 409
        
        # Add new contact
        new_contact = {
            "First Name": first_name,
            "Last Name": last_name,
            "Email Address": email,
            "Company": data.get('company', ''),
            "Job Title": data.get('jobTitle', ''),
            "Business City": data.get('city', ''),
            "Business State": data.get('state', ''),
        }
        
        contacts.append(new_contact)
        
        # Save to CSV
        save_contacts(contacts)
        
        return jsonify({
            "success": True,
            "contact": {
                "firstName": first_name,
                "lastName": last_name,
                "email": email,
                "company": new_contact["Company"],
                "jobTitle": new_contact["Job Title"],
                "status": "pending" if email else "no-email"
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/contacts/<email>', methods=['DELETE'])
@require_api_key
def delete_contact(email):
    """Delete a contact by email."""
    try:
        contacts = load_contacts()
        
        # Find and remove contact
        original_len = len(contacts)
        contacts = [c for c in contacts if c.get("Email Address", "").strip().lower() != email.lower()]
        
        if len(contacts) == original_len:
            return jsonify({"error": "Contact not found"}), 404
        
        # Save to CSV
        save_contacts(contacts)
        
        return jsonify({"success": True, "message": f"Contact {email} deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def save_contacts(contacts: list) -> None:
    """Save contacts list to CSV file."""
    fieldnames = ["First Name", "Last Name", "Email Address", "Company", "Job Title", "Business City", "Business State"]
    
    with open(DEFAULT_CONTACTS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(contacts)


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get configuration."""
    try:
        config = load_config()
        return jsonify(config)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/config', methods=['POST'])
@require_api_key
def save_config():
    """Save configuration."""
    try:
        config = request.json
        with open(DEFAULT_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get email logs."""
    try:
        logs = []
        if os.path.exists(DEFAULT_LOG_FILE):
            with open(DEFAULT_LOG_FILE, newline='', encoding='utf-8') as f:
                content = f.read()
                if content.startswith("\ufeff"):
                    content = content[1:]
                reader = csv.DictReader(StringIO(content))
                for row in reader:
                    logs.append({
                        "timestamp": row.get("Timestamp", ""),
                        "email": row.get("Email", ""),
                        "company": row.get("Company", ""),
                        "status": row.get("Status", ""),
                        "subject": row.get("Subject", ""),
                        "error": row.get("Error", "")
                    })
        
        # Return in reverse chronological order
        logs.reverse()
        return jsonify({"logs": logs, "total": len(logs)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/dry-run', methods=['POST'])
@require_api_key
def dry_run():
    """Generate email drafts without sending."""
    try:
        data = request.json or {}
        limit = data.get('limit', 5)
        email_filter = data.get('email')  # Optional: specific email to generate for
        
        config = load_config()
        contacts = load_contacts()
        contacted = load_contacted_emails()
        
        # Filter contacts
        contacts = [c for c in contacts if c.get("Email Address", "").strip()]
        
        if email_filter:
            contacts = [c for c in contacts if c.get("Email Address", "").strip().lower() == email_filter.lower()]
        else:
            # Filter out already contacted
            contacts = [c for c in contacts if c.get("Email Address", "").strip().lower() not in contacted]
        
        contacts = contacts[:limit]
        
        if not contacts:
            return jsonify({
                "success": True,
                "drafts": [],
                "message": "No new contacts to process"
            })
        
        drafts = []
        for contact in contacts:
            try:
                subject, body = generate_personalized_email(contact, config)
                filename = save_draft(contact, subject, body)
                append_log(contact, "DRY_RUN", subject)
                
                drafts.append({
                    "recipient": f"{contact.get('First Name', '')} {contact.get('Last Name', '')}".strip(),
                    "email": contact.get("Email Address", ""),
                    "company": contact.get("Company", ""),
                    "subject": subject,
                    "body": body,
                    "preview": body[:150] + "..." if len(body) > 150 else body,
                    "filename": filename,
                    "date": datetime.now().isoformat()
                })
            except Exception as e:
                append_log(contact, "ERROR", "N/A", str(e))
                drafts.append({
                    "recipient": f"{contact.get('First Name', '')} {contact.get('Last Name', '')}".strip(),
                    "email": contact.get("Email Address", ""),
                    "error": str(e)
                })
        
        return jsonify({
            "success": True,
            "drafts": drafts,
            "count": len([d for d in drafts if 'error' not in d])
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/send', methods=['POST'])
@require_api_key
def send_email_endpoint():
    """Send emails to contacts."""
    try:
        data = request.json or {}
        limit = min(data.get('limit', 1), 50)  # Cap at 50 emails per request
        email_filter = data.get('email')  # Optional: specific email to send to
        
        # Validate email filter if provided
        if email_filter and not validate_email(email_filter):
            return jsonify({"error": "Invalid email format"}), 400
        
        config = load_config()
        contacts = load_contacts()
        contacted = load_contacted_emails()
        
        # Get Gmail service
        service = get_gmail_service()
        
        # Filter contacts with valid emails
        contacts = [
            c for c in contacts 
            if c.get("Email Address", "").strip() and validate_email(c.get("Email Address", "").strip())
        ]
        
        if email_filter:
            contacts = [c for c in contacts if c.get("Email Address", "").strip().lower() == email_filter.lower()]
        else:
            # Filter out already contacted
            contacts = [c for c in contacts if c.get("Email Address", "").strip().lower() not in contacted]
        
        contacts = contacts[:limit]
        
        if not contacts:
            return jsonify({
                "success": True,
                "sent": [],
                "message": "No new contacts to send to"
            })
        
        sent = []
        for contact in contacts:
            email = contact.get("Email Address", "").strip()
            try:
                subject, body = generate_personalized_email(contact, config)
                
                msg = create_message(
                    sender_name=config["your_name"],
                    sender_email=config["your_email"],
                    to=email,
                    subject=subject,
                    body_text=body,
                )
                send_message(service, "me", msg)
                append_log(contact, "SENT", subject)
                
                sent.append({
                    "recipient": f"{contact.get('First Name', '')} {contact.get('Last Name', '')}".strip(),
                    "email": email,
                    "company": contact.get("Company", ""),
                    "subject": subject,
                    "status": "sent"
                })
            except Exception as e:
                append_log(contact, "ERROR", "N/A", str(e))
                sent.append({
                    "recipient": f"{contact.get('First Name', '')} {contact.get('Last Name', '')}".strip(),
                    "email": email,
                    "error": str(e),
                    "status": "error"
                })
        
        return jsonify({
            "success": True,
            "sent": sent,
            "count": len([s for s in sent if s.get('status') == 'sent'])
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/drafts', methods=['GET'])
def get_drafts():
    """Get saved drafts from the drafts directory."""
    try:
        drafts = []
        if os.path.exists(DEFAULT_DRAFTS_DIR):
            for filename in os.listdir(DEFAULT_DRAFTS_DIR):
                if filename.endswith('.txt'):
                    filepath = os.path.join(DEFAULT_DRAFTS_DIR, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    lines = content.split('\n')
                    to_email = ""
                    subject = ""
                    body = ""
                    
                    for i, line in enumerate(lines):
                        if line.startswith("TO: "):
                            to_email = line[4:].strip()
                        elif line.startswith("SUBJECT: "):
                            subject = line[9:].strip()
                        elif line.startswith("-" * 10):
                            body = '\n'.join(lines[i+2:]).strip()
                            break
                    
                    # Parse name from filename
                    name_parts = filename.replace('.txt', '').split('_')
                    first_name = name_parts[0] if len(name_parts) > 0 else ""
                    last_name = name_parts[1] if len(name_parts) > 1 else ""
                    company = name_parts[2] if len(name_parts) > 2 else ""
                    
                    drafts.append({
                        "filename": filename,
                        "recipient": f"{first_name} {last_name}".strip(),
                        "email": to_email,
                        "company": company.replace('_', ' '),
                        "subject": subject,
                        "body": body,
                        "preview": body[:150] + "..." if len(body) > 150 else body,
                        "date": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
                    })
        
        # Sort by date descending
        drafts.sort(key=lambda x: x['date'], reverse=True)
        return jsonify({"drafts": drafts, "total": len(drafts)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Outreach API Server')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode (development only)')
    parser.add_argument('--port', type=int, default=5000, help='Port to run on')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    args = parser.parse_args()
    
    # Use environment variable or command line for debug mode
    debug_mode = args.debug or os.environ.get('FLASK_DEBUG', '').lower() == 'true'
    
    print("\n🚀 Outreach API Server")
    print("=" * 40)
    print(f"📂 Base directory: {BASE_DIR}")
    print(f"🌐 API running at: http://{args.host}:{args.port}")
    print(f"🔧 Debug mode: {'ON' if debug_mode else 'OFF'}")
    print("=" * 40)
    print("\nEndpoints:")
    print("  GET  /api/health   - Health check")
    print("  GET  /api/contacts - Get contacts")
    print("  GET  /api/config   - Get config")
    print("  POST /api/config   - Save config")
    print("  GET  /api/logs     - Get email logs")
    print("  POST /api/dry-run  - Generate drafts")
    print("  POST /api/send     - Send emails")
    print("  GET  /api/drafts   - Get saved drafts")
    print("\nPress Ctrl+C to stop\n")
    
    if debug_mode:
        print("⚠️  WARNING: Running in debug mode. Do not use in production!\n")
    
    app.run(host=args.host, port=args.port, debug=debug_mode)
