"""
Tests for the Outreach project.

Run with: pytest tests/
"""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from outreach_proj.outreach import (
    load_config,
    load_contacts,
    load_contacted_emails,
    save_draft,
)


class TestLoadConfig:
    """Tests for config loading."""
    
    def test_load_config_success(self, tmp_path):
        """Test loading a valid config file."""
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
    
    def test_load_config_missing_file(self):
        """Test loading a non-existent config file."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.json")


class TestLoadContacts:
    """Tests for contact loading."""
    
    def test_load_contacts_success(self, tmp_path):
        """Test loading valid contacts CSV."""
        csv_content = """First Name,Last Name,Email Address,Company,Job Title
John,Doe,john@example.com,Acme Corp,Engineer
Jane,Smith,jane@example.com,Tech Inc,Designer"""
        
        contacts_file = tmp_path / "contacts.csv"
        contacts_file.write_text(csv_content)
        
        result = load_contacts(str(contacts_file))
        
        assert len(result) == 2
        assert result[0]["First Name"] == "John"
        assert result[0]["Email Address"] == "john@example.com"
        assert result[1]["Company"] == "Tech Inc"
    
    def test_load_contacts_with_bom(self, tmp_path):
        """Test loading CSV with BOM character."""
        csv_content = "\ufeffFirst Name,Last Name,Email Address\nJohn,Doe,john@example.com"
        
        contacts_file = tmp_path / "contacts.csv"
        contacts_file.write_text(csv_content, encoding='utf-8-sig')
        
        result = load_contacts(str(contacts_file))
        
        assert len(result) == 1
        assert result[0]["First Name"] == "John"


class TestLoadContactedEmails:
    """Tests for contacted emails tracking."""
    
    def test_load_contacted_emails_empty(self, tmp_path):
        """Test with non-existent log file."""
        result = load_contacted_emails(str(tmp_path / "nonexistent.csv"))
        assert result == set()
    
    def test_load_contacted_emails_with_sent(self, tmp_path):
        """Test loading emails with SENT status."""
        log_content = """Timestamp,Email,Company,Status,Subject,Error
2024-01-01T10:00:00,john@example.com,Acme,SENT,Hello,
2024-01-01T11:00:00,jane@example.com,Tech,DRY_RUN,Test,
2024-01-01T12:00:00,error@example.com,Bad,ERROR,Failed,Connection timeout"""
        
        log_file = tmp_path / "logs.csv"
        log_file.write_text(log_content)
        
        result = load_contacted_emails(str(log_file))
        
        assert "john@example.com" in result
        assert "jane@example.com" in result
        assert "error@example.com" not in result  # ERROR status not included


class TestSaveDraft:
    """Tests for draft saving."""
    
    def test_save_draft_creates_file(self, tmp_path):
        """Test that save_draft creates a file."""
        contact = {
            "First Name": "John",
            "Last Name": "Doe",
            "Company": "Acme",
            "Email Address": "john@example.com"
        }
        subject = "Test Subject"
        body = "Test body content"
        
        result = save_draft(contact, subject, body, str(tmp_path))
        
        assert result == "John_Doe_Acme.txt"
        
        draft_path = tmp_path / "John_Doe_Acme.txt"
        assert draft_path.exists()
        
        content = draft_path.read_text()
        assert "TO: john@example.com" in content
        assert "SUBJECT: Test Subject" in content
        assert "Test body content" in content


class TestEmailValidation:
    """Tests for email validation patterns."""
    
    @pytest.mark.parametrize("email,expected", [
        ("test@example.com", True),
        ("user.name@domain.org", True),
        ("user+tag@gmail.com", True),
        ("invalid", False),
        ("missing@domain", False),
        ("@nodomain.com", False),
        ("spaces in@email.com", False),
    ])
    def test_email_validation(self, email, expected):
        """Test email validation pattern."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        result = bool(re.match(pattern, email))
        assert result == expected


class TestGenerateEmail:
    """Tests for email generation (mocked)."""
    
    @patch('outreach_proj.generate_email.client')
    def test_generate_email_success(self, mock_client):
        """Test successful email generation."""
        from outreach_proj.generate_email import generate_personalized_email
        
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "subject": "Test Subject",
            "body": "Hi John,\n\nTest email body."
        })
        mock_client.chat.completions.create.return_value = mock_response
        
        contact = {
            "First Name": "John",
            "Last Name": "Doe",
            "Company": "Acme Corp",
            "Job Title": "Engineer",
            "Email Address": "john@example.com"
        }
        config = {
            "your_name": "Test User",
            "your_email": "test@example.com",
            "your_school": "Test University"
        }
        
        subject, body = generate_personalized_email(contact, config)
        
        assert subject == "Test Subject"
        assert "Hi John" in body
        assert "Test User" in body  # Signature should be added
    
    @patch('outreach_proj.generate_email.client')
    def test_generate_email_fallback_on_error(self, mock_client):
        """Test fallback when OpenAI fails."""
        from outreach_proj.generate_email import generate_personalized_email
        
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        contact = {
            "First Name": "John",
            "Company": "Acme",
            "Job Title": "Engineer"
        }
        config = {
            "your_name": "Test User",
            "your_school": "Test U"
        }
        
        subject, body = generate_personalized_email(contact, config)
        
        # Should return fallback email
        assert "Acme" in subject or "Acme" in body
        assert "John" in body


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
