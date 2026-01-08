"""
Email generation and sending service.

Handles AI-powered email generation and delivery.
"""

import json
import logging
from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session

from openai import OpenAI

from ..config import config
from ..models import (
    User, Contact, Template, Campaign, CampaignContact, 
    EmailLog, EmailStatus, UserProfile
)

logger = logging.getLogger(__name__)


class EmailService:
    """Service for generating and sending emails."""
    
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
    
    def _get_user_profile_dict(self) -> dict:
        """Get user profile as a dictionary for template rendering."""
        profile = self.user.profile
        if not profile:
            return {"full_name": self.user.email}
        
        return {
            "full_name": profile.full_name,
            "sender_email": profile.sender_email or self.user.email,
            "phone": profile.phone,
            "title": profile.title,
            "organization": profile.organization,
            "department": profile.department,
            "major": profile.major,
            "graduation_year": profile.graduation_year,
            "pitch": profile.pitch,
            "target_goal": profile.target_goal,
            "skills": profile.skills,
            "experience": profile.experience,
            "signature_template": profile.signature_template,
        }
    
    def _get_contact_dict(self, contact: Contact) -> dict:
        """Get contact as a dictionary for template rendering."""
        return {
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "email": contact.email,
            "company": contact.company,
            "job_title": contact.job_title,
            "city": contact.city,
            "state": contact.state,
        }
    
    def _build_signature(self) -> str:
        """Build email signature from user profile."""
        profile = self.user.profile
        if not profile:
            return f"Best,\n{self.user.email}"
        
        # Use custom signature if provided
        if profile.signature_template:
            return profile.signature_template
        
        # Build default signature
        lines = ["Best,", profile.full_name]
        
        if profile.title:
            lines.append(profile.title)
        
        if profile.organization or profile.department:
            org_line = " | ".join(filter(None, [profile.organization, profile.department]))
            lines.append(org_line)
        
        if profile.major:
            degree_line = f"B.S. {profile.major}"
            if profile.graduation_year:
                degree_line += f", Class of {profile.graduation_year}"
            lines.append(degree_line)
        
        contact_parts = [
            p for p in [profile.sender_email or self.user.email, profile.phone] 
            if p
        ]
        if contact_parts:
            lines.append(" | ".join(contact_parts))
        
        return "\n".join(lines)
    
    def generate_email(
        self, 
        contact: Contact, 
        template: Optional[Template] = None,
    ) -> tuple[str, str]:
        """
        Generate a personalized email for a contact.
        
        Args:
            contact: The contact to generate email for
            template: Template to use (or default if None)
            
        Returns:
            Tuple of (subject, body)
        """
        from .template_service import TemplateService
        
        # Get template
        if not template:
            template_service = TemplateService(self.db, self.user)
            template = template_service.get_default()
        
        if not template:
            # Fallback to basic generation
            return self._generate_fallback_email(contact)
        
        # Render prompts
        user_profile = self._get_user_profile_dict()
        contact_data = self._get_contact_dict(contact)
        
        template_service = TemplateService(self.db, self.user)
        system_prompt, user_prompt = template_service.render_prompt(
            template, contact_data, user_profile
        )
        
        # Call OpenAI
        try:
            response = self.openai_client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt or "You return ONLY valid JSON objects."},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=config.OPENAI_TEMPERATURE,
            )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")
            
            content = content.strip()
            
            # Clean markdown code fences if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            data = json.loads(content)
            
            # Handle list response
            if isinstance(data, list):
                data = data[0] if data else {}
            
            subject = data.get("subject", f"Interest in {contact.company or 'your company'}")
            body_content = data.get("body", f"Hi {contact.first_name},\n\nI'd love to connect.")
            
            # Add signature
            signature = self._build_signature()
            full_body = f"{body_content}\n\n{signature}"
            
            return subject, full_body
            
        except Exception as e:
            logger.error(f"Error generating email for {contact.email}: {e}")
            return self._generate_fallback_email(contact)
    
    def _generate_fallback_email(self, contact: Contact) -> tuple[str, str]:
        """Generate a simple fallback email if AI fails."""
        profile = self.user.profile
        sender_name = profile.full_name if profile else "there"
        organization = profile.organization if profile else ""
        
        subject = f"Interest in {contact.company or 'your company'}"
        body = (
            f"Hi {contact.first_name or 'there'},\n\n"
            f"I hope this email finds you well. "
            f"I'm {sender_name}{f' from {organization}' if organization else ''}, "
            f"and I'm reaching out because I'm interested in learning more about "
            f"your work{f' at {contact.company}' if contact.company else ''}.\n\n"
            f"{self._build_signature()}"
        )
        
        return subject, body
    
    def log_email(
        self,
        contact: Contact,
        status: EmailStatus,
        subject: Optional[str] = None,
        campaign: Optional[Campaign] = None,
        error_message: Optional[str] = None,
    ) -> EmailLog:
        """Log an email activity."""
        log = EmailLog(
            user_id=self.user.id,
            contact_id=contact.id,
            campaign_id=campaign.id if campaign else None,
            recipient_email=contact.email or "",
            recipient_name=contact.full_name,
            company=contact.company,
            subject=subject,
            status=status,
            error_message=error_message,
        )
        self.db.add(log)
        self.db.flush()
        return log
    
    def get_logs(
        self, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[EmailStatus] = None,
    ) -> list[EmailLog]:
        """Get email logs for the current user."""
        query = self.db.query(EmailLog).filter(EmailLog.user_id == self.user.id)
        
        if status:
            query = query.filter(EmailLog.status == status)
        
        return query.order_by(EmailLog.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_contacted_emails(self) -> set[str]:
        """Get set of email addresses that have been contacted."""
        logs = (
            self.db.query(EmailLog.recipient_email)
            .filter(
                EmailLog.user_id == self.user.id,
                EmailLog.status.in_([EmailStatus.SENT, EmailStatus.DRAFT])
            )
            .distinct()
            .all()
        )
        return {log[0].lower() for log in logs if log[0]}
    
    def get_stats(self) -> dict:
        """Get email statistics for the current user."""
        from sqlalchemy import func
        
        total_sent = (
            self.db.query(EmailLog)
            .filter(
                EmailLog.user_id == self.user.id,
                EmailLog.status == EmailStatus.SENT
            )
            .count()
        )
        
        total_failed = (
            self.db.query(EmailLog)
            .filter(
                EmailLog.user_id == self.user.id,
                EmailLog.status == EmailStatus.FAILED
            )
            .count()
        )
        
        total_drafts = (
            self.db.query(EmailLog)
            .filter(
                EmailLog.user_id == self.user.id,
                EmailLog.status == EmailStatus.DRAFT
            )
            .count()
        )
        
        return {
            "sent": total_sent,
            "failed": total_failed,
            "drafts": total_drafts,
            "success_rate": round(total_sent / (total_sent + total_failed) * 100, 1) if (total_sent + total_failed) > 0 else 0,
        }
