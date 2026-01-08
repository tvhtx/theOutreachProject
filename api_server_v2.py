#!/usr/bin/env python3
"""
Flask API server for the Outreach application (v2).

This version adds user authentication and database support while
maintaining backward compatibility with the original API.
"""

import os
import sys
import time
import re
from datetime import datetime
from functools import wraps
from flask import Flask, jsonify, request, g
from flask_cors import CORS

# Add the project to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from outreach_proj.config import config
from outreach_proj.database import init_db, get_db_session
from outreach_proj.models import User, Contact, Template, EmailLog, EmailStatus
from outreach_proj.auth import (
    require_auth, require_auth_optional, 
    create_access_token, create_user, authenticate_user
)
from outreach_proj.services import ContactService, TemplateService, EmailService

# ========================================
# App Configuration
# ========================================

app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY

# CORS Configuration
CORS(app, origins=config.ALLOWED_ORIGINS, supports_credentials=True)

# Rate limiting (simple in-memory)
rate_limit_cache = {}


# ========================================
# Utilities
# ========================================

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


# ========================================
# Request Hooks
# ========================================

@app.before_request
def before_request():
    """Run before each request."""
    if not rate_limit():
        return jsonify({"error": "Rate limit exceeded. Please wait."}), 429
    
    g.start_time = time.time()
    g.db = get_db_session()


@app.teardown_request
def teardown_request(exception=None):
    """Clean up database session."""
    db = g.pop('db', None)
    if db is not None:
        if exception:
            db.rollback()
        else:
            try:
                db.commit()
            except:
                db.rollback()
        db.close()


# ========================================
# Health Check
# ========================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "ok", 
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    })


# ========================================
# Authentication Endpoints
# ========================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.json or {}
    
    email = data.get('email', '').strip()
    password = data.get('password', '')
    full_name = data.get('fullName', data.get('full_name', '')).strip()
    
    # Validation
    if not email or not validate_email(email):
        return jsonify({"error": "Valid email is required"}), 400
    
    if not password or len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    
    if not full_name:
        return jsonify({"error": "Full name is required"}), 400
    
    # Create user
    user, error = create_user(email, password, full_name)
    if error:
        return jsonify({"error": error}), 400
    
    # Create default templates for new user
    try:
        template_service = TemplateService(g.db, user)
        template_service.create_defaults()
        g.db.commit()
    except Exception as e:
        app.logger.warning(f"Could not create default templates: {e}")
    
    # Generate token
    token = create_access_token(user.id, user.email)
    
    return jsonify({
        "success": True,
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "fullName": full_name,
        }
    }), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login and get access token."""
    data = request.json or {}
    
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    user, error = authenticate_user(email, password)
    if error:
        return jsonify({"error": error}), 401
    
    token = create_access_token(user.id, user.email)
    
    profile = user.profile
    
    return jsonify({
        "success": True,
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "fullName": profile.full_name if profile else user.email,
        }
    })


@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get current authenticated user."""
    user = g.current_user
    profile = user.profile
    
    return jsonify({
        "id": user.id,
        "email": user.email,
        "fullName": profile.full_name if profile else user.email,
        "isVerified": user.is_verified,
        "createdAt": user.created_at.isoformat() if user.created_at else None,
        "profile": {
            "phone": profile.phone if profile else None,
            "title": profile.title if profile else None,
            "organization": profile.organization if profile else None,
            "department": profile.department if profile else None,
            "major": profile.major if profile else None,
            "graduationYear": profile.graduation_year if profile else None,
            "pitch": profile.pitch if profile else None,
            "targetGoal": profile.target_goal if profile else None,
            "senderEmail": profile.sender_email if profile else user.email,
        } if profile else None
    })


@app.route('/api/auth/profile', methods=['PUT'])
@require_auth
def update_profile():
    """Update user profile."""
    data = request.json or {}
    user = g.current_user
    
    profile = user.profile
    if not profile:
        from outreach_proj.models import UserProfile
        profile = UserProfile(user_id=user.id, full_name=user.email)
        g.db.add(profile)
    
    # Update fields
    if 'fullName' in data:
        profile.full_name = data['fullName']
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
    if 'graduationYear' in data:
        profile.graduation_year = data['graduationYear']
    if 'pitch' in data:
        profile.pitch = data['pitch']
    if 'targetGoal' in data:
        profile.target_goal = data['targetGoal']
    if 'senderEmail' in data:
        profile.sender_email = data['senderEmail']
    if 'skills' in data:
        profile.skills = data['skills']
    if 'experience' in data:
        profile.experience = data['experience']
    if 'signatureTemplate' in data:
        profile.signature_template = data['signatureTemplate']
    
    return jsonify({"success": True})


# ========================================
# Contacts Endpoints
# ========================================

@app.route('/api/contacts', methods=['GET'])
@require_auth
def get_contacts():
    """Get all contacts for the current user."""
    user = g.current_user
    
    # Query params
    skip = request.args.get('skip', 0, type=int)
    limit = request.args.get('limit', 100, type=int)
    status = request.args.get('status')
    company = request.args.get('company')
    search = request.args.get('search')
    
    service = ContactService(g.db, user)
    contacts = service.get_all(skip=skip, limit=limit, status=status, company=company, search=search)
    total = service.get_count()
    
    # Get contacted emails for status
    email_service = EmailService(g.db, user)
    contacted = email_service.get_contacted_emails()
    
    result = []
    for c in contacts:
        email = (c.email or "").lower()
        contact_status = c.status
        if not email:
            contact_status = "no-email"
        elif email in contacted:
            contact_status = "sent"
        
        result.append({
            "id": c.id,
            "firstName": c.first_name,
            "lastName": c.last_name,
            "email": c.email,
            "company": c.company,
            "jobTitle": c.job_title,
            "city": c.city,
            "state": c.state,
            "phone": c.phone,
            "status": contact_status,
            "notes": c.notes,
            "createdAt": c.created_at.isoformat() if c.created_at else None,
        })
    
    return jsonify({"contacts": result, "total": total})


@app.route('/api/contacts', methods=['POST'])
@require_auth
def add_contact():
    """Add a new contact."""
    data = request.json or {}
    user = g.current_user
    
    first_name = data.get('firstName', '').strip()
    if not first_name:
        return jsonify({"error": "First name is required"}), 400
    
    email = data.get('email', '').strip()
    if email and not validate_email(email):
        return jsonify({"error": "Invalid email format"}), 400
    
    service = ContactService(g.db, user)
    
    # Check for duplicate
    if email and service.get_by_email(email):
        return jsonify({"error": "A contact with this email already exists"}), 409
    
    contact = service.create(
        first_name=first_name,
        last_name=data.get('lastName', '').strip() or None,
        email=email or None,
        company=data.get('company', '').strip() or None,
        job_title=data.get('jobTitle', '').strip() or None,
        city=data.get('city', '').strip() or None,
        state=data.get('state', '').strip() or None,
        phone=data.get('phone', '').strip() or None,
        notes=data.get('notes', '').strip() or None,
    )
    
    return jsonify({
        "success": True,
        "contact": {
            "id": contact.id,
            "firstName": contact.first_name,
            "lastName": contact.last_name,
            "email": contact.email,
            "company": contact.company,
            "jobTitle": contact.job_title,
            "status": "pending" if contact.email else "no-email",
        }
    }), 201


@app.route('/api/contacts/<int:contact_id>', methods=['PUT'])
@require_auth
def update_contact(contact_id):
    """Update a contact."""
    data = request.json or {}
    user = g.current_user
    
    service = ContactService(g.db, user)
    
    # Map camelCase to snake_case
    update_data = {}
    field_map = {
        'firstName': 'first_name',
        'lastName': 'last_name',
        'email': 'email',
        'company': 'company',
        'jobTitle': 'job_title',
        'city': 'city',
        'state': 'state',
        'phone': 'phone',
        'notes': 'notes',
        'status': 'status',
    }
    
    for camel, snake in field_map.items():
        if camel in data:
            update_data[snake] = data[camel]
    
    contact = service.update(contact_id, **update_data)
    if not contact:
        return jsonify({"error": "Contact not found"}), 404
    
    return jsonify({"success": True})


@app.route('/api/contacts/<int:contact_id>', methods=['DELETE'])
@require_auth
def delete_contact_by_id(contact_id):
    """Delete a contact by ID."""
    user = g.current_user
    service = ContactService(g.db, user)
    
    if not service.delete(contact_id):
        return jsonify({"error": "Contact not found"}), 404
    
    return jsonify({"success": True})


@app.route('/api/contacts/<email>', methods=['DELETE'])
@require_auth
def delete_contact_by_email(email):
    """Delete a contact by email (legacy endpoint)."""
    user = g.current_user
    service = ContactService(g.db, user)
    
    contact = service.get_by_email(email)
    if not contact:
        return jsonify({"error": "Contact not found"}), 404
    
    service.delete(contact.id)
    return jsonify({"success": True, "message": f"Contact {email} deleted"})


@app.route('/api/contacts/import', methods=['POST'])
@require_auth
def import_contacts():
    """Import contacts from CSV."""
    user = g.current_user
    
    if 'file' not in request.files:
        # Try to get CSV content from JSON body
        data = request.json or {}
        csv_content = data.get('csv', '')
    else:
        file = request.files['file']
        csv_content = file.read().decode('utf-8')
    
    if not csv_content:
        return jsonify({"error": "No CSV content provided"}), 400
    
    service = ContactService(g.db, user)
    imported, errors = service.import_from_csv(csv_content)
    
    return jsonify({
        "success": True,
        "imported": imported,
        "errors": errors[:10],  # Limit errors returned
        "totalErrors": len(errors),
    })


@app.route('/api/contacts/export', methods=['GET'])
@require_auth
def export_contacts():
    """Export contacts to CSV."""
    user = g.current_user
    service = ContactService(g.db, user)
    
    csv_content = service.export_to_csv()
    
    return csv_content, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=contacts.csv'
    }


@app.route('/api/contacts/stats', methods=['GET'])
@require_auth
def get_contact_stats():
    """Get contact statistics."""
    user = g.current_user
    service = ContactService(g.db, user)
    
    return jsonify(service.get_stats())


# ========================================
# Templates Endpoints
# ========================================

@app.route('/api/templates', methods=['GET'])
@require_auth
def get_templates():
    """Get all templates for the current user."""
    user = g.current_user
    category = request.args.get('category')
    
    service = TemplateService(g.db, user)
    templates = service.get_all(category=category)
    
    return jsonify({
        "templates": [{
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "category": t.category,
            "isDefault": t.is_default,
            "subjectTemplate": t.subject_template,
            "bodyTemplate": t.body_template,
            "systemPrompt": t.system_prompt,
            "userPromptTemplate": t.user_prompt_template,
        } for t in templates],
        "total": len(templates),
    })


@app.route('/api/templates', methods=['POST'])
@require_auth
def create_template():
    """Create a new template."""
    data = request.json or {}
    user = g.current_user
    
    name = data.get('name', '').strip()
    if not name:
        return jsonify({"error": "Template name is required"}), 400
    
    service = TemplateService(g.db, user)
    template = service.create(
        name=name,
        description=data.get('description'),
        category=data.get('category'),
        subject_template=data.get('subjectTemplate'),
        body_template=data.get('bodyTemplate'),
        system_prompt=data.get('systemPrompt'),
        user_prompt_template=data.get('userPromptTemplate'),
        is_default=data.get('isDefault', False),
    )
    
    return jsonify({
        "success": True,
        "template": {
            "id": template.id,
            "name": template.name,
        }
    }), 201


@app.route('/api/templates/<int:template_id>', methods=['PUT'])
@require_auth
def update_template(template_id):
    """Update a template."""
    data = request.json or {}
    user = g.current_user
    
    service = TemplateService(g.db, user)
    
    update_data = {}
    field_map = {
        'name': 'name',
        'description': 'description',
        'category': 'category',
        'subjectTemplate': 'subject_template',
        'bodyTemplate': 'body_template',
        'systemPrompt': 'system_prompt',
        'userPromptTemplate': 'user_prompt_template',
        'isDefault': 'is_default',
        'isActive': 'is_active',
    }
    
    for camel, snake in field_map.items():
        if camel in data:
            update_data[snake] = data[camel]
    
    template = service.update(template_id, **update_data)
    if not template:
        return jsonify({"error": "Template not found"}), 404
    
    return jsonify({"success": True})


@app.route('/api/templates/<int:template_id>', methods=['DELETE'])
@require_auth
def delete_template(template_id):
    """Delete a template."""
    user = g.current_user
    service = TemplateService(g.db, user)
    
    if not service.delete(template_id):
        return jsonify({"error": "Template not found"}), 404
    
    return jsonify({"success": True})


# ========================================
# Email Generation & Sending
# ========================================

@app.route('/api/generate', methods=['POST'])
@require_auth
def generate_email():
    """Generate an email for a contact."""
    data = request.json or {}
    user = g.current_user
    
    contact_id = data.get('contactId')
    template_id = data.get('templateId')
    
    if not contact_id:
        return jsonify({"error": "contactId is required"}), 400
    
    contact_service = ContactService(g.db, user)
    contact = contact_service.get_by_id(contact_id)
    if not contact:
        return jsonify({"error": "Contact not found"}), 404
    
    template = None
    if template_id:
        template_service = TemplateService(g.db, user)
        template = template_service.get_by_id(template_id)
    
    email_service = EmailService(g.db, user)
    subject, body = email_service.generate_email(contact, template)
    
    return jsonify({
        "success": True,
        "email": {
            "subject": subject,
            "body": body,
            "recipient": contact.full_name,
            "recipientEmail": contact.email,
            "company": contact.company,
        }
    })


@app.route('/api/logs', methods=['GET'])
@require_auth
def get_logs():
    """Get email logs."""
    user = g.current_user
    skip = request.args.get('skip', 0, type=int)
    limit = request.args.get('limit', 100, type=int)
    
    email_service = EmailService(g.db, user)
    logs = email_service.get_logs(skip=skip, limit=limit)
    
    return jsonify({
        "logs": [{
            "id": log.id,
            "timestamp": log.created_at.isoformat() if log.created_at else None,
            "email": log.recipient_email,
            "name": log.recipient_name,
            "company": log.company,
            "subject": log.subject,
            "status": log.status.value if log.status else None,
            "error": log.error_message,
        } for log in logs],
        "total": len(logs),
    })


@app.route('/api/stats', methods=['GET'])
@require_auth
def get_stats():
    """Get overall statistics."""
    user = g.current_user
    
    contact_service = ContactService(g.db, user)
    email_service = EmailService(g.db, user)
    
    contact_stats = contact_service.get_stats()
    email_stats = email_service.get_stats()
    
    return jsonify({
        "contacts": contact_stats,
        "emails": email_stats,
    })


# ========================================
# Legacy Endpoints (Backward Compatibility)
# ========================================
# These endpoints maintain compatibility with the original API
# They work without authentication if API_KEY is not set

def require_legacy_auth(f):
    """Legacy API key authentication (optional)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not config.API_KEY:
            return f(*args, **kwargs)
        
        provided_key = request.headers.get('X-API-Key')
        if not provided_key or provided_key != config.API_KEY:
            return jsonify({"error": "Invalid or missing API key"}), 401
        
        return f(*args, **kwargs)
    return decorated


@app.route('/api/config', methods=['GET'])
@require_legacy_auth
def get_config_legacy():
    """Get configuration (legacy endpoint)."""
    try:
        import json
        config_path = config.LEGACY_CONFIG_FILE
        with open(config_path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/config', methods=['POST'])
@require_legacy_auth
def save_config_legacy():
    """Save configuration (legacy endpoint)."""
    try:
        import json
        config_data = request.json
        config_path = config.LEGACY_CONFIG_FILE
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========================================
# Main Entry Point
# ========================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Outreach API Server v2')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    parser.add_argument('--port', type=int, default=config.API_PORT, help='Port to run on')
    parser.add_argument('--host', default=config.API_HOST, help='Host to bind to')
    parser.add_argument('--init-db', action='store_true', help='Initialize database')
    args = parser.parse_args()
    
    # Initialize database if requested
    if args.init_db:
        print("Initializing database...")
        init_db()
        print("Database initialized!")
        sys.exit(0)
    
    debug_mode = args.debug or config.FLASK_DEBUG
    
    # Auto-initialize database on first run
    try:
        init_db()
    except Exception as e:
        print(f"Note: Could not initialize database: {e}")
    
    print("\n🚀 Outreach API Server v2")
    print("=" * 40)
    print(f"📂 Base directory: {BASE_DIR}")
    print(f"🌐 API running at: http://{args.host}:{args.port}")
    print(f"🔧 Debug mode: {'ON' if debug_mode else 'OFF'}")
    print(f"🗄️  Database: {config.DATABASE_URL}")
    print("=" * 40)
    print("\nNew Endpoints:")
    print("  POST /api/auth/register - Create account")
    print("  POST /api/auth/login    - Get access token")
    print("  GET  /api/auth/me       - Get current user")
    print("  GET  /api/contacts      - Get contacts (auth required)")
    print("  GET  /api/templates     - Get templates (auth required)")
    print("  POST /api/generate      - Generate email (auth required)")
    print("  GET  /api/stats         - Get statistics (auth required)")
    print("\nLegacy endpoints still available for backward compatibility")
    print("\nPress Ctrl+C to stop\n")
    
    if debug_mode:
        print("⚠️  WARNING: Running in debug mode. Do not use in production!\n")
    
    app.run(host=args.host, port=args.port, debug=debug_mode)
