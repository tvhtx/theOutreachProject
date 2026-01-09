#!/usr/bin/env python3
"""
Flask API server for the Outreach frontend.
Provides endpoints for authentication, contacts, campaigns, and email functionality.

Now supports multi-tenant user authentication with JWT tokens.
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

# Import configuration and database
from outreach_proj.config import config
from outreach_proj.database import init_db, get_db_session
from outreach_proj.models import User, UserProfile

# Import auth utilities
from outreach_proj.auth import (
    require_auth,
    require_auth_optional,
    create_access_token,
    create_user,
    authenticate_user,
)

# Import service helpers
from outreach_proj.api_helpers import (
    get_contact_service,
    get_template_service,
    get_email_service,
)

# Legacy imports (for backwards compatibility during migration)
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

# Initialize database on startup
init_db()

# CORS Configuration
CORS(app, origins=config.ALLOWED_ORIGINS, supports_credentials=True)

# Rate limiting cache (per IP)
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
        if current_time - t < config.RATE_LIMIT_WINDOW
    ]
    
    if len(rate_limit_cache[client_ip]) >= config.RATE_LIMIT_MAX_REQUESTS:
        return False
    
    rate_limit_cache[client_ip].append(current_time)
    return True


def require_api_key(f):
    """Decorator to require legacy API key authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip auth if no API key is configured
        if not config.API_KEY:
            return f(*args, **kwargs)
        
        # Check for API key in header
        provided_key = request.headers.get('X-API-Key')
        if not provided_key or provided_key != config.API_KEY:
            return jsonify({"error": "Invalid or missing API key"}), 401
        
        return f(*args, **kwargs)
    return decorated_function


@app.before_request
def before_request():
    """Run before each request - rate limiting and logging."""
    # Skip rate limiting for auth endpoints during development
    if request.endpoint in ['login', 'register', 'health_check']:
        g.start_time = time.time()
        return
    
    # Rate limiting
    if not rate_limit():
        return jsonify({"error": "Rate limit exceeded. Please wait."}), 429
    
    g.start_time = time.time()


# ========================================
# Authentication Endpoints
# ========================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user account."""
    try:
        data = request.json or {}
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        full_name = data.get('name', '').strip()
        
        # Validation
        if not email or not validate_email(email):
            return jsonify({"error": "Valid email is required"}), 400
        
        if not password or len(password) < 8:
            return jsonify({"error": "Password must be at least 8 characters"}), 400
        
        if not full_name:
            return jsonify({"error": "Name is required"}), 400
        
        # Create user
        user, error = create_user(email, password, full_name)
        
        if error:
            return jsonify({"error": error}), 400
        
        # Generate token
        token = create_access_token(user.id, user.email)
        
        return jsonify({
            "success": True,
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.profile.full_name if user.profile else full_name,
            }
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token."""
    try:
        data = request.json or {}
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
        
        # Authenticate
        user, error = authenticate_user(email, password)
        
        if error:
            return jsonify({"error": error}), 401
        
        # Generate token
        token = create_access_token(user.id, user.email)
        
        return jsonify({
            "success": True,
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.profile.full_name if user.profile else "",
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get current authenticated user's information."""
    try:
        user = g.current_user
        profile = user.profile
        
        return jsonify({
            "id": user.id,
            "email": user.email,
            "name": profile.full_name if profile else "",
            "profile": {
                "phone": profile.phone if profile else None,
                "title": profile.title if profile else None,
                "organization": profile.organization if profile else None,
                "department": profile.department if profile else None,
                "major": profile.major if profile else None,
                "graduation_year": profile.graduation_year if profile else None,
                "pitch": profile.pitch if profile else None,
                "target_goal": profile.target_goal if profile else None,
                "sender_email": profile.sender_email if profile else user.email,
            },
            "created_at": user.created_at.isoformat() if user.created_at else None,
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/auth/profile', methods=['PUT'])
@require_auth
def update_profile():
    """Update current user's profile."""
    try:
        user = g.current_user
        data = request.json or {}
        
        db = get_db_session()
        try:
            from outreach_proj.models import UserProfile
            
            profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
            
            if not profile:
                profile = UserProfile(user_id=user.id, full_name=data.get('name', 'User'))
                db.add(profile)
            
            # Update fields
            if 'name' in data:
                profile.full_name = data['name']
            if 'phone' in data:
                profile.phone = data['phone']
            if 'title' in data:
                profile.title = data['title']
            if 'organization' in data:
                profile.organization = data['organization']
            if 'department' in data:
                profile.department = data['department']
            if 'major' in data:
                profile.major = data['major']
            if 'graduation_year' in data:
                profile.graduation_year = data['graduation_year']
            if 'pitch' in data:
                profile.pitch = data['pitch']
            if 'target_goal' in data:
                profile.target_goal = data['target_goal']
            if 'sender_email' in data:
                profile.sender_email = data['sender_email']
            
            db.commit()
            
            return jsonify({
                "success": True,
                "message": "Profile updated successfully"
            })
            
        finally:
            db.close()
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========================================
# Health Check
# ========================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "ok", 
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "database": "connected"
    })


# ========================================
# Contacts API (Database-backed with Auth)
# ========================================

@app.route('/api/v2/contacts', methods=['GET'])
@require_auth
def get_contacts_v2():
    """Get all contacts for the authenticated user (database-backed)."""
    try:
        with get_contact_service() as service:
            # Get query parameters
            status = request.args.get('status')
            company = request.args.get('company')
            search = request.args.get('search')
            limit = request.args.get('limit', 100, type=int)
            offset = request.args.get('offset', 0, type=int)
            
            contacts = service.get_all(
                skip=offset,
                limit=limit,
                status=status,
                company=company,
                search=search,
            )
            
            return jsonify({
                "contacts": [{
                    "id": c.id,
                    "firstName": c.first_name,
                    "lastName": c.last_name or "",
                    "email": c.email or "",
                    "company": c.company or "",
                    "jobTitle": c.job_title or "",
                    "city": c.city or "",
                    "state": c.state or "",
                    "status": c.status or "pending",
                } for c in contacts],
                "total": len(contacts)
            })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v2/contacts', methods=['POST'])
@require_auth
def create_contact_v2():
    """Create a new contact for the authenticated user (database-backed)."""
    try:
        data = request.json or {}
        
        # Validate
        if not data.get('firstName'):
            return jsonify({"error": "First name is required"}), 400
        
        email = data.get('email', '').strip()
        if email and not validate_email(email):
            return jsonify({"error": "Invalid email format"}), 400
        
        with get_contact_service() as service:
            # Check for duplicate email
            if email and service.get_by_email(email):
                return jsonify({"error": "Contact with this email already exists"}), 400
            
            contact = service.create(
                first_name=data.get('firstName', '').strip(),
                last_name=data.get('lastName', '').strip() or None,
                email=email or None,
                company=data.get('company', '').strip() or None,
                job_title=data.get('jobTitle', '').strip() or None,
                city=data.get('city', '').strip() or None,
                state=data.get('state', '').strip() or None,
                notes=data.get('notes', '').strip() or None,
            )
            
            return jsonify({
                "success": True,
                "contact": {
                    "id": contact.id,
                    "firstName": contact.first_name,
                    "lastName": contact.last_name or "",
                    "email": contact.email or "",
                    "company": contact.company or "",
                    "jobTitle": contact.job_title or "",
                    "status": contact.status or "pending",
                }
            }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v2/contacts/<int:contact_id>', methods=['GET'])
@require_auth
def get_contact_v2(contact_id):
    """Get a specific contact by ID."""
    try:
        with get_contact_service() as service:
            contact = service.get_by_id(contact_id)
            
            if not contact:
                return jsonify({"error": "Contact not found"}), 404
            
            return jsonify({
                "id": contact.id,
                "firstName": contact.first_name,
                "lastName": contact.last_name or "",
                "email": contact.email or "",
                "company": contact.company or "",
                "jobTitle": contact.job_title or "",
                "city": contact.city or "",
                "state": contact.state or "",
                "phone": contact.phone or "",
                "linkedinUrl": contact.linkedin_url or "",
                "notes": contact.notes or "",
                "status": contact.status or "pending",
                "lastContactedAt": contact.last_contacted_at.isoformat() if contact.last_contacted_at else None,
                "createdAt": contact.created_at.isoformat() if contact.created_at else None,
            })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v2/contacts/<int:contact_id>', methods=['PUT'])
@require_auth
def update_contact_v2(contact_id):
    """Update a contact."""
    try:
        data = request.json or {}
        
        email = data.get('email', '').strip()
        if email and not validate_email(email):
            return jsonify({"error": "Invalid email format"}), 400
        
        with get_contact_service() as service:
            # Build update kwargs (only include non-None values)
            update_data = {}
            if 'firstName' in data:
                update_data['first_name'] = data['firstName']
            if 'lastName' in data:
                update_data['last_name'] = data['lastName']
            if email:
                update_data['email'] = email
            if 'company' in data:
                update_data['company'] = data['company']
            if 'jobTitle' in data:
                update_data['job_title'] = data['jobTitle']
            if 'city' in data:
                update_data['city'] = data['city']
            if 'state' in data:
                update_data['state'] = data['state']
            if 'phone' in data:
                update_data['phone'] = data['phone']
            if 'linkedinUrl' in data:
                update_data['linkedin_url'] = data['linkedinUrl']
            if 'notes' in data:
                update_data['notes'] = data['notes']
            if 'status' in data:
                update_data['status'] = data['status']
            
            contact = service.update(contact_id, **update_data)
            
            if not contact:
                return jsonify({"error": "Contact not found"}), 404
            
            return jsonify({
                "success": True,
                "contact": {
                    "id": contact.id,
                    "firstName": contact.first_name,
                    "lastName": contact.last_name or "",
                    "email": contact.email or "",
                    "status": contact.status or "pending",
                }
            })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v2/contacts/<int:contact_id>', methods=['DELETE'])
@require_auth
def delete_contact_v2(contact_id):
    """Delete a contact."""
    try:
        with get_contact_service() as service:
            success = service.delete(contact_id)
            
            if not success:
                return jsonify({"error": "Contact not found"}), 404
            
            return jsonify({"success": True, "message": "Contact deleted"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v2/contacts/import', methods=['POST'])
@require_auth
def import_contacts_v2():
    """Import contacts from CSV data."""
    try:
        data = request.json or {}
        csv_content = data.get('csv', '')
        
        if not csv_content:
            return jsonify({"error": "No CSV content provided"}), 400
        
        with get_contact_service() as service:
            imported, errors = service.import_from_csv(csv_content)
            
            return jsonify({
                "success": True,
                "imported": imported,
                "errors": errors
            })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========================================
# Templates API (Database-backed with Auth)
# ========================================

@app.route('/api/v2/templates', methods=['GET'])
@require_auth
def get_templates():
    """Get all templates for the authenticated user."""
    try:
        with get_template_service() as service:
            category = request.args.get('category')
            templates = service.get_all(category=category)
            
            return jsonify({
                "templates": [{
                    "id": t.id,
                    "name": t.name,
                    "description": t.description or "",
                    "category": t.category or "",
                    "isDefault": t.is_default,
                    "isActive": t.is_active,
                } for t in templates],
                "total": len(templates)
            })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v2/templates/<int:template_id>', methods=['GET'])
@require_auth
def get_template(template_id):
    """Get a specific template with full content."""
    try:
        with get_template_service() as service:
            template = service.get_by_id(template_id)
            
            if not template:
                return jsonify({"error": "Template not found"}), 404
            
            return jsonify({
                "id": template.id,
                "name": template.name,
                "description": template.description or "",
                "category": template.category or "",
                "subjectTemplate": template.subject_template or "",
                "bodyTemplate": template.body_template or "",
                "systemPrompt": template.system_prompt or "",
                "userPromptTemplate": template.user_prompt_template or "",
                "isDefault": template.is_default,
                "isActive": template.is_active,
            })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========================================
# Legacy Contacts API (File-based, no auth required)
# These endpoints maintain backwards compatibility
# ========================================

@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    """Get all contacts (legacy - file-based)."""
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
    
    print("\n🚀 Outreach API Server v2.0")
    print("=" * 50)
    print(f"📂 Base directory: {BASE_DIR}")
    print(f"🌐 API running at: http://{args.host}:{args.port}")
    print(f"🔧 Debug mode: {'ON' if debug_mode else 'OFF'}")
    print(f"🗄️  Database: {config.DATABASE_URL}")
    print("=" * 50)
    
    print("\n📡 Authentication Endpoints:")
    print("  POST /api/auth/register   - Create new account")
    print("  POST /api/auth/login      - Login & get JWT token")
    print("  GET  /api/auth/me         - Get current user [Auth]")
    print("  PUT  /api/auth/profile    - Update profile [Auth]")
    
    print("\n📇 Contacts API v2 (Database + Auth):")
    print("  GET    /api/v2/contacts           - List contacts [Auth]")
    print("  POST   /api/v2/contacts           - Create contact [Auth]")
    print("  GET    /api/v2/contacts/<id>      - Get contact [Auth]")
    print("  PUT    /api/v2/contacts/<id>      - Update contact [Auth]")
    print("  DELETE /api/v2/contacts/<id>      - Delete contact [Auth]")
    print("  POST   /api/v2/contacts/import    - Import contacts [Auth]")
    
    print("\n📝 Templates API v2:")
    print("  GET  /api/v2/templates            - List templates [Auth]")
    print("  GET  /api/v2/templates/<id>       - Get template [Auth]")
    
    print("\n📋 Legacy Endpoints (file-based, no auth):")
    print("  GET  /api/health    - Health check")
    print("  GET  /api/contacts  - Get contacts (CSV)")
    print("  GET  /api/config    - Get config")
    print("  POST /api/config    - Save config")
    print("  GET  /api/logs      - Get email logs")
    print("  POST /api/dry-run   - Generate drafts")
    print("  POST /api/send      - Send emails")
    print("  GET  /api/drafts    - Get saved drafts")
    
    print("\nPress Ctrl+C to stop\n")
    
    if debug_mode:
        print("⚠️  WARNING: Running in debug mode. Do not use in production!\n")
    
    app.run(host=args.host, port=args.port, debug=debug_mode)
