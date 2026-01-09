"""
Tests for the Outreach project.

Run with: pytest tests/ -v
"""

import json
import os
import sys
import tempfile
import uuid
from unittest.mock import MagicMock, patch

import pytest

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ========================================
# Configuration Tests
# ========================================

class TestConfig:
    """Tests for configuration loading."""
    
    def test_config_loads(self):
        """Test that config loads from environment."""
        from outreach_proj.config import config
        
        assert config.API_HOST is not None
        assert config.API_PORT is not None
        assert config.DATABASE_URL is not None
    
    def test_config_has_required_attrs(self):
        """Test config has required attributes."""
        from outreach_proj.config import config
        
        assert hasattr(config, 'SECRET_KEY')
        assert hasattr(config, 'JWT_ALGORITHM')
        assert hasattr(config, 'JWT_EXPIRATION_HOURS')


# ========================================
# Database Tests
# ========================================

class TestDatabase:
    """Tests for database operations."""
    
    def test_init_db(self):
        """Test database initialization creates tables."""
        from outreach_proj.database import init_db, engine
        from outreach_proj.models import Base
        
        # Init should not raise
        init_db()
        
        # Check tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        assert 'users' in tables
        assert 'contacts' in tables
        assert 'templates' in tables
        assert 'campaigns' in tables


# ========================================
# Authentication Tests
# ========================================

class TestAuthentication:
    """Tests for authentication utilities."""
    
    def test_hash_password(self):
        """Test password hashing."""
        from outreach_proj.auth import hash_password, verify_password
        
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrongpassword", hashed)
    
    def test_create_access_token_returns_string(self):
        """Test JWT token creation returns a string."""
        from outreach_proj.auth import create_access_token
        
        token = create_access_token(123, "test@example.com")
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_invalid_token(self):
        """Test decoding invalid token returns None."""
        from outreach_proj.auth import decode_access_token
        
        result = decode_access_token("invalid.token.here")
        
        assert result is None


# ========================================
# Model Tests
# ========================================

class TestModels:
    """Tests for database models."""
    
    def test_contact_model_creation(self):
        """Test Contact model instantiation."""
        from outreach_proj.models import Contact
        
        contact = Contact(
            user_id=1,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            company="Acme Corp"
        )
        
        assert contact.first_name == "John"
        assert contact.last_name == "Doe"
        assert contact.full_name == "John Doe"
    
    def test_campaign_status_enum(self):
        """Test CampaignStatus enum values."""
        from outreach_proj.models import CampaignStatus
        
        assert CampaignStatus.DRAFT.value == "draft"
        assert CampaignStatus.RUNNING.value == "running"
        assert CampaignStatus.COMPLETED.value == "completed"
    
    def test_email_status_enum(self):
        """Test EmailStatus enum values."""
        from outreach_proj.models import EmailStatus
        
        assert EmailStatus.PENDING.value == "pending"
        assert EmailStatus.SENT.value == "sent"
        assert EmailStatus.FAILED.value == "failed"
    
    def test_user_model(self):
        """Test User model instantiation."""
        from outreach_proj.models import User
        
        user = User(
            email="test@example.com",
            password_hash="hashedpassword"
        )
        
        assert user.email == "test@example.com"
        assert str(user) == "<User test@example.com>"


# ========================================
# Legacy Outreach Tests
# ========================================

class TestLegacyOutreach:
    """Tests for legacy outreach functions."""
    
    def test_load_config_success(self, tmp_path):
        """Test loading a valid config file."""
        from outreach_proj.outreach import load_config
        
        config_data = {
            "your_name": "Test User",
            "your_email": "test@example.com",
            "your_school": "Test University"
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))
        
        result = load_config(str(config_file))
        
        assert result["your_name"] == "Test User"
        assert result["your_email"] == "test@example.com"
    
    def test_load_contacts_success(self, tmp_path):
        """Test loading valid contacts CSV."""
        from outreach_proj.outreach import load_contacts
        
        csv_content = """First Name,Last Name,Email Address,Company,Job Title
John,Doe,john@example.com,Acme Corp,Engineer
Jane,Smith,jane@example.com,Tech Inc,Designer"""
        
        contacts_file = tmp_path / "contacts.csv"
        contacts_file.write_text(csv_content)
        
        result = load_contacts(str(contacts_file))
        
        assert len(result) == 2
        assert result[0]["First Name"] == "John"
        assert result[0]["Email Address"] == "john@example.com"
    
    def test_load_contacted_emails_empty(self, tmp_path):
        """Test with non-existent log file."""
        from outreach_proj.outreach import load_contacted_emails
        
        result = load_contacted_emails(str(tmp_path / "nonexistent.csv"))
        
        assert result == set()


# ========================================
# Email Validation Tests
# ========================================

class TestEmailValidation:
    """Tests for email validation."""
    
    @pytest.mark.parametrize("email,expected", [
        ("test@example.com", True),
        ("user.name@domain.org", True),
        ("user+tag@gmail.com", True),
        ("invalid", False),
        ("missing@domain", False),
        ("@nodomain.com", False),
    ])
    def test_email_validation_pattern(self, email, expected):
        """Test email validation pattern."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        result = bool(re.match(pattern, email))
        assert result == expected


# ========================================
# API Integration Tests
# ========================================

class TestAPIIntegration:
    """Integration tests for API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from api_server import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
        assert 'timestamp' in data
        assert data.get('version') == '2.0.0'
    
    def test_login_invalid(self, client):
        """Test login with invalid credentials."""
        response = client.post('/api/auth/login',
            json={
                'email': 'nonexistent@example.com',
                'password': 'wrongpassword'
            }
        )
        
        assert response.status_code == 401
    
    def test_protected_endpoint_no_auth(self, client):
        """Test protected endpoint without auth returns 401."""
        response = client.get('/api/auth/me')
        
        assert response.status_code == 401
    
    def test_legacy_contacts_endpoint(self, client):
        """Test legacy contacts endpoint works without auth."""
        response = client.get('/api/contacts')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'contacts' in data
    
    def test_v2_contacts_requires_auth(self, client):
        """Test v2 contacts endpoint requires auth."""
        response = client.get('/api/v2/contacts')
        
        assert response.status_code == 401
    
    def test_v2_templates_requires_auth(self, client):
        """Test v2 templates endpoint requires auth."""
        response = client.get('/api/v2/templates')
        
        assert response.status_code == 401
    
    def test_register_validation(self, client):
        """Test registration validation."""
        # Missing email
        response = client.post('/api/auth/register', 
            json={'password': 'test123', 'name': 'Test'}
        )
        assert response.status_code == 400
        
        # Missing password
        response = client.post('/api/auth/register', 
            json={'email': 'test@example.com', 'name': 'Test'}
        )
        assert response.status_code == 400
        
        # Missing name
        response = client.post('/api/auth/register', 
            json={'email': 'test@example.com', 'password': 'test123'}
        )
        assert response.status_code == 400


# ========================================
# Service Tests
# ========================================

class TestContactService:
    """Tests for ContactService."""
    
    @pytest.fixture
    def db_session(self):
        """Create a test database session."""
        from outreach_proj.database import SessionLocal, init_db
        init_db()
        session = SessionLocal()
        yield session
        session.rollback()
        session.close()
    
    @pytest.fixture
    def test_user(self, db_session):
        """Create a unique test user."""
        from outreach_proj.models import User, UserProfile
        from outreach_proj.auth import hash_password
        
        unique_email = f'testservice_{uuid.uuid4().hex[:8]}@example.com'
        
        user = User(
            email=unique_email,
            password_hash=hash_password("testpass123")
        )
        db_session.add(user)
        db_session.flush()
        
        profile = UserProfile(
            user_id=user.id,
            full_name="Test Service User"
        )
        db_session.add(profile)
        db_session.commit()
        
        return user
    
    def test_create_contact(self, db_session, test_user):
        """Test creating a contact."""
        from outreach_proj.services.contact_service import ContactService
        
        service = ContactService(db_session, test_user)
        
        unique_email = f'contact_{uuid.uuid4().hex[:8]}@example.com'
        contact = service.create(
            first_name="Test",
            last_name="Contact",
            email=unique_email,
            company="Test Company"
        )
        
        assert contact.id is not None
        assert contact.first_name == "Test"
        assert contact.email == unique_email.lower()
        assert contact.user_id == test_user.id
    
    def test_get_contacts(self, db_session, test_user):
        """Test getting contacts."""
        from outreach_proj.services.contact_service import ContactService
        
        service = ContactService(db_session, test_user)
        
        # Create a few contacts
        service.create(first_name="Contact1", email=f'c1_{uuid.uuid4().hex[:8]}@test.com')
        service.create(first_name="Contact2", email=f'c2_{uuid.uuid4().hex[:8]}@test.com')
        
        contacts = service.get_all()
        
        assert len(contacts) >= 2
    
    def test_update_contact(self, db_session, test_user):
        """Test updating a contact."""
        from outreach_proj.services.contact_service import ContactService
        
        service = ContactService(db_session, test_user)
        
        # Create a contact
        contact = service.create(
            first_name="Original",
            email=f'update_{uuid.uuid4().hex[:8]}@test.com'
        )
        
        # Update it
        updated = service.update(contact.id, first_name="Updated")
        
        assert updated is not None
        assert updated.first_name == "Updated"
    
    def test_delete_contact(self, db_session, test_user):
        """Test deleting a contact."""
        from outreach_proj.services.contact_service import ContactService
        
        service = ContactService(db_session, test_user)
        
        # Create a contact
        contact = service.create(
            first_name="ToDelete",
            email=f'delete_{uuid.uuid4().hex[:8]}@test.com'
        )
        contact_id = contact.id
        
        # Delete it
        result = service.delete(contact_id)
        
        assert result == True
        assert service.get_by_id(contact_id) is None
    
    def test_contacts_are_user_scoped(self, db_session, test_user):
        """Test that contacts are scoped to user."""
        from outreach_proj.services.contact_service import ContactService
        from outreach_proj.models import User, UserProfile
        from outreach_proj.auth import hash_password
        
        # Create another user
        other_email = f'other_{uuid.uuid4().hex[:8]}@example.com'
        other_user = User(
            email=other_email,
            password_hash=hash_password("pass123")
        )
        db_session.add(other_user)
        db_session.flush()
        
        profile = UserProfile(user_id=other_user.id, full_name="Other User")
        db_session.add(profile)
        db_session.commit()
        
        # Create contact for other user
        other_contact_email = f'othercontact_{uuid.uuid4().hex[:8]}@test.com'
        other_service = ContactService(db_session, other_user)
        other_service.create(first_name="OtherContact", email=other_contact_email)
        
        # Original user should not see other user's contacts
        service = ContactService(db_session, test_user)
        contacts = service.get_all()
        emails = [c.email for c in contacts]
        
        assert other_contact_email.lower() not in emails


class TestTemplateService:
    """Tests for TemplateService."""
    
    @pytest.fixture
    def db_session(self):
        """Create a test database session."""
        from outreach_proj.database import SessionLocal, init_db
        init_db()
        session = SessionLocal()
        yield session
        session.rollback()
        session.close()
    
    @pytest.fixture
    def test_user(self, db_session):
        """Create a unique test user."""
        from outreach_proj.models import User, UserProfile
        from outreach_proj.auth import hash_password
        
        unique_email = f'templatetest_{uuid.uuid4().hex[:8]}@example.com'
        
        user = User(
            email=unique_email,
            password_hash=hash_password("testpass123")
        )
        db_session.add(user)
        db_session.flush()
        
        profile = UserProfile(
            user_id=user.id,
            full_name="Template Test User"
        )
        db_session.add(profile)
        db_session.commit()
        
        return user
    
    def test_create_template(self, db_session, test_user):
        """Test creating a template."""
        from outreach_proj.services.template_service import TemplateService
        
        service = TemplateService(db_session, test_user)
        
        template = service.create(
            name="Test Template",
            description="A test template",
            category="networking"
        )
        
        assert template.id is not None
        assert template.name == "Test Template"
        assert template.user_id == test_user.id
    
    def test_get_templates(self, db_session, test_user):
        """Test getting templates."""
        from outreach_proj.services.template_service import TemplateService
        
        service = TemplateService(db_session, test_user)
        
        # Create templates
        service.create(name="Template 1")
        service.create(name="Template 2")
        
        templates = service.get_all()
        
        assert len(templates) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
