"""
SQLAlchemy database models for the Outreach application.

This module defines all database tables for multi-tenant user support.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey,
    JSON, Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class CampaignStatus(enum.Enum):
    """Status of a campaign."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EmailStatus(enum.Enum):
    """Status of an individual email."""
    PENDING = "pending"
    DRAFT = "draft"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"


class User(Base):
    """User account for the application."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="user", cascade="all, delete-orphan")
    templates = relationship("Template", back_populates="user", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="user", cascade="all, delete-orphan")
    email_logs = relationship("EmailLog", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.email}>"


class UserProfile(Base):
    """Extended profile information for a user (used in email signatures)."""
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Personal info
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    
    # Professional/Educational info
    title = Column(String(255), nullable=True)  # e.g., "Lead Engineer | Baja Racing"
    organization = Column(String(255), nullable=True)  # e.g., "Baylor University"
    department = Column(String(255), nullable=True)  # e.g., "School of Engineering"
    major = Column(String(255), nullable=True)
    graduation_year = Column(String(10), nullable=True)
    
    # Outreach content
    pitch = Column(Text, nullable=True)  # Brief intro about yourself
    target_goal = Column(Text, nullable=True)  # What you're looking for
    
    # Email settings
    sender_email = Column(String(255), nullable=True)  # Email to send from
    signature_template = Column(Text, nullable=True)  # Custom signature format
    
    # Skills and experience for AI prompt
    skills = Column(Text, nullable=True)  # JSON or plain text
    experience = Column(Text, nullable=True)  # JSON or plain text
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="profile")
    
    def __repr__(self):
        return f"<UserProfile {self.full_name}>"


class Contact(Base):
    """A contact that can receive outreach emails."""
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Basic info
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    
    # Professional info
    company = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    
    # Location
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    
    # Contact details
    phone = Column(String(50), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    
    # Custom fields (JSON for flexibility)
    custom_fields = Column(JSON, nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Tracking
    status = Column(String(50), default="pending")  # pending, contacted, replied, not_interested
    last_contacted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="contacts")
    campaign_contacts = relationship("CampaignContact", back_populates="contact", cascade="all, delete-orphan")
    email_logs = relationship("EmailLog", back_populates="contact", cascade="all, delete-orphan")
    
    # Unique constraint: one email per user
    __table_args__ = (
        UniqueConstraint('user_id', 'email', name='uq_user_contact_email'),
        Index('ix_contacts_user_company', 'user_id', 'company'),
    )
    
    def __repr__(self):
        return f"<Contact {self.first_name} {self.last_name} ({self.email})>"
    
    @property
    def full_name(self) -> str:
        """Get full name of contact."""
        parts = [self.first_name or "", self.last_name or ""]
        return " ".join(p for p in parts if p).strip() or "Unknown"


class Template(Base):
    """Email template for generating outreach emails."""
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Template info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)  # e.g., "networking", "sales", "recruitment"
    
    # Template content
    subject_template = Column(String(500), nullable=True)  # Can include {{variables}}
    body_template = Column(Text, nullable=True)  # Full email template
    
    # AI Prompt configuration
    system_prompt = Column(Text, nullable=True)  # System message for AI
    user_prompt_template = Column(Text, nullable=True)  # User prompt with {{variables}}
    
    # Settings
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="templates")
    campaigns = relationship("Campaign", back_populates="template")
    
    def __repr__(self):
        return f"<Template {self.name}>"


class Campaign(Base):
    """An email campaign targeting multiple contacts."""
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("templates.id", ondelete="SET NULL"), nullable=True)
    
    # Campaign info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Status
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.DRAFT)
    
    # Scheduling
    scheduled_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Statistics (denormalized for quick access)
    total_contacts = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    
    # Settings
    send_delay_min = Column(Integer, default=15)  # seconds between emails
    send_delay_max = Column(Integer, default=45)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="campaigns")
    template = relationship("Template", back_populates="campaigns")
    campaign_contacts = relationship("CampaignContact", back_populates="campaign", cascade="all, delete-orphan")
    email_logs = relationship("EmailLog", back_populates="campaign")
    
    def __repr__(self):
        return f"<Campaign {self.name} ({self.status.value})>"


class CampaignContact(Base):
    """Association between a campaign and a contact."""
    __tablename__ = "campaign_contacts"
    
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    
    # Draft content (editable before sending)
    draft_subject = Column(String(500), nullable=True)
    draft_body = Column(Text, nullable=True)
    
    # Status
    status = Column(SQLEnum(EmailStatus), default=EmailStatus.PENDING)
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="campaign_contacts")
    contact = relationship("Contact", back_populates="campaign_contacts")
    
    __table_args__ = (
        UniqueConstraint('campaign_id', 'contact_id', name='uq_campaign_contact'),
    )
    
    def __repr__(self):
        return f"<CampaignContact campaign={self.campaign_id} contact={self.contact_id}>"


class EmailLog(Base):
    """Log of all email activity."""
    __tablename__ = "email_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True)
    
    # Email details
    recipient_email = Column(String(255), nullable=False)
    recipient_name = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=True)
    
    # Status
    status = Column(SQLEnum(EmailStatus), nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="email_logs")
    contact = relationship("Contact", back_populates="email_logs")
    campaign = relationship("Campaign", back_populates="email_logs")
    
    def __repr__(self):
        return f"<EmailLog {self.recipient_email} - {self.status.value}>"


# ========================================
# Default Templates
# ========================================

# Anti-spam rules to embed in all templates
_ANTI_SPAM_RULES = """
## QUALITY RULES (CRITICAL - violating these makes the email feel like spam):
1. NEVER use "I hope this email finds you well" or any variant.
2. NEVER use "reaching out" - just state your purpose directly.
3. NEVER use "touch base", "synergy", "leverage", or corporate buzzwords.
4. NEVER use more than ONE exclamation point in the entire email.
5. NEVER ask for a meeting or call in the first email. Ask a question instead.
6. Keep the email under 100 words (excluding greeting and sign-off line).
7. Sound like a curious human, not a salesperson.
8. Be specific - mention ONE thing about their role/company that's genuinely interesting.
9. The subject line should be lowercase and conversational (e.g., "quick question about your work at {{company}}").
"""

DEFAULT_TEMPLATES = [
    {
        "name": "Professional Networking",
        "description": "Genuine networking outreach that gets replies, not spam flags",
        "category": "networking",
        "system_prompt": f"""You are a writing assistant helping craft genuine networking emails.
Your goal is to write emails that sound like they came from a real person who is genuinely curious.

{_ANTI_SPAM_RULES}

## TONE:
- Conversational, like you're texting a colleague
- Humble but not self-deprecating
- Curious, not transactional
- Specific, not generic

## OUTPUT FORMAT:
Return ONLY valid JSON with "subject" and "body" keys. No markdown, no extra text.""",
        "user_prompt_template": """
**WHO I AM:**
Name: {{sender_name}}
Background: {{sender_pitch}}
What I'm looking for: {{sender_goal}}

**WHO I'M WRITING TO:**
Name: {{recipient_first_name}}
Role: {{recipient_job_title}}
Company: {{recipient_company}}

**TASK:**
Write a short networking email (under 100 words). I want to learn from their experience, not ask for a job.
Do NOT include a signature - it gets added automatically.

Return ONLY: {"subject": "...", "body": "Hi {{recipient_first_name}}, ..."}
"""
    },
    {
        "name": "Sales - Value First",
        "description": "Cold outreach focused on giving value, not asking for a meeting",
        "category": "sales",
        "system_prompt": f"""You are a sales email writer focused on providing value, not pitching.
The goal of email #1 is to start a conversation, NOT to book a meeting.

{_ANTI_SPAM_RULES}

## SALES-SPECIFIC RULES:
- Lead with an insight or observation about their company
- Offer something useful (a resource, idea, or question)
- Do NOT pitch your product in email #1
- End with a low-commitment question, not a meeting request

## OUTPUT FORMAT:
Return ONLY valid JSON with "subject" and "body" keys.""",
        "user_prompt_template": """
**SENDER:**
Name: {{sender_name}}
Company: {{sender_organization}}
What we do: {{sender_pitch}}

**RECIPIENT:**
Name: {{recipient_first_name}}
Role: {{recipient_job_title}}
Company: {{recipient_company}}

**TASK:**
Write a value-first cold email. DO NOT ask for a meeting. Just start a conversation.
No signature needed.

Return ONLY: {"subject": "...", "body": "..."}
"""
    },
    {
        "name": "Student Outreach",
        "description": "For students seeking internships, mentorship, or career advice",
        "category": "networking",
        "system_prompt": f"""You are helping a student write genuine networking emails to professionals.
Students have an advantage: people WANT to help students. Lean into curiosity and humility.

{_ANTI_SPAM_RULES}

## STUDENT-SPECIFIC RULES:
- Lead with genuine curiosity about their career path
- Mention ONE specific thing you're working on (shows you're serious)
- Ask a specific question they'd enjoy answering
- Don't ask for an internship directly - ask for advice

## OUTPUT FORMAT:
Return ONLY valid JSON with "subject" and "body" keys.""",
        "user_prompt_template": """
**STUDENT:**
Name: {{sender_name}}
School: {{sender_organization}}
Major: {{sender_major}}
Graduation: {{sender_graduation_year}}
Relevant work: {{sender_pitch}}
Goal: {{sender_goal}}

**PROFESSIONAL:**
Name: {{recipient_first_name}}
Role: {{recipient_job_title}}
Company: {{recipient_company}}

**TASK:**
Write an email showing genuine interest in their career. Ask for advice, not a job.
No signature.

Return ONLY: {"subject": "...", "body": "Hi {{recipient_first_name}}, ..."}
"""
    },
]
