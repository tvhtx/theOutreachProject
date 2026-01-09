"""
Template management service.

Handles CRUD operations for email templates.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from ..models import Template, User, DEFAULT_TEMPLATES


class TemplateService:
    """Service for managing email templates."""
    
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
    
    def get_all(
        self, 
        category: Optional[str] = None,
        active_only: bool = True,
    ) -> list[Template]:
        """Get all templates for the current user."""
        query = self.db.query(Template).filter(Template.user_id == self.user.id)
        
        if active_only:
            query = query.filter(Template.is_active == True)
        
        if category:
            query = query.filter(Template.category == category)
        
        return query.order_by(Template.is_default.desc(), Template.name).all()
    
    def get_by_id(self, template_id: int) -> Optional[Template]:
        """Get a template by ID (scoped to current user)."""
        return self.db.query(Template).filter(
            Template.id == template_id,
            Template.user_id == self.user.id
        ).first()
    
    def get_default(self) -> Optional[Template]:
        """Get the default template for the current user."""
        return self.db.query(Template).filter(
            Template.user_id == self.user.id,
            Template.is_default == True,
            Template.is_active == True
        ).first()
    
    def create(
        self,
        name: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        subject_template: Optional[str] = None,
        body_template: Optional[str] = None,
        system_prompt: Optional[str] = None,
        user_prompt_template: Optional[str] = None,
        is_default: bool = False,
    ) -> Template:
        """Create a new template."""
        # If setting as default, unset other defaults
        if is_default:
            self.db.query(Template).filter(
                Template.user_id == self.user.id
            ).update({"is_default": False})
        
        template = Template(
            user_id=self.user.id,
            name=name,
            description=description,
            category=category,
            subject_template=subject_template,
            body_template=body_template,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            is_default=is_default,
        )
        self.db.add(template)
        self.db.flush()
        return template
    
    def update(self, template_id: int, **kwargs) -> Optional[Template]:
        """Update a template's fields."""
        template = self.get_by_id(template_id)
        if not template:
            return None
        
        # Handle is_default specially
        if kwargs.get('is_default', False):
            self.db.query(Template).filter(
                Template.user_id == self.user.id
            ).update({"is_default": False})
        
        for key, value in kwargs.items():
            if hasattr(template, key) and key not in ('id', 'user_id', 'created_at'):
                setattr(template, key, value)
        
        template.updated_at = datetime.utcnow()
        self.db.flush()
        return template
    
    def delete(self, template_id: int) -> bool:
        """Delete a template."""
        template = self.get_by_id(template_id)
        if not template:
            return False
        
        self.db.delete(template)
        self.db.flush()
        return True
    
    def duplicate(self, template_id: int, new_name: Optional[str] = None) -> Optional[Template]:
        """Create a copy of an existing template."""
        original = self.get_by_id(template_id)
        if not original:
            return None
        
        return self.create(
            name=new_name or f"{original.name} (Copy)",
            description=original.description,
            category=original.category,
            subject_template=original.subject_template,
            body_template=original.body_template,
            system_prompt=original.system_prompt,
            user_prompt_template=original.user_prompt_template,
            is_default=False,
        )
    
    def create_defaults(self) -> list[Template]:
        """Create default templates for a new user."""
        templates = []
        
        for i, template_data in enumerate(DEFAULT_TEMPLATES):
            template = self.create(
                name=template_data["name"],
                description=template_data.get("description"),
                category=template_data.get("category"),
                system_prompt=template_data.get("system_prompt"),
                user_prompt_template=template_data.get("user_prompt_template"),
                is_default=(i == 0),  # First template is default
            )
            templates.append(template)
        
        return templates
    
    def render_prompt(
        self, 
        template: Template, 
        contact_data: dict, 
        user_profile_data: dict
    ) -> tuple[str, str]:
        """
        Render the template prompts with given data.
        
        Args:
            template: The template to render
            contact_data: Contact information dict
            user_profile_data: User profile information dict
            
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        # Merge data for variable substitution
        variables = {
            # Sender (user) variables
            "sender_name": user_profile_data.get("full_name", ""),
            "sender_email": user_profile_data.get("sender_email", ""),
            "sender_organization": user_profile_data.get("organization", ""),
            "sender_major": user_profile_data.get("major", ""),
            "sender_graduation_year": user_profile_data.get("graduation_year", ""),
            "sender_title": user_profile_data.get("title", ""),
            "sender_pitch": user_profile_data.get("pitch", ""),
            "sender_goal": user_profile_data.get("target_goal", ""),
            "sender_skills": user_profile_data.get("skills", ""),
            "sender_experience": user_profile_data.get("experience", ""),
            
            # Recipient (contact) variables
            "recipient_first_name": contact_data.get("first_name", "there"),
            "recipient_last_name": contact_data.get("last_name", ""),
            "recipient_email": contact_data.get("email", ""),
            "recipient_company": contact_data.get("company", "your company"),
            "recipient_job_title": contact_data.get("job_title", "your role"),
            "recipient_city": contact_data.get("city", ""),
            "recipient_state": contact_data.get("state", ""),
        }
        
        system_prompt = template.system_prompt or ""
        user_prompt = template.user_prompt_template or ""
        
        # Simple variable substitution using {{variable_name}}
        for key, value in variables.items():
            system_prompt = system_prompt.replace(f"{{{{{key}}}}}", str(value or ""))
            user_prompt = user_prompt.replace(f"{{{{{key}}}}}", str(value or ""))
        
        return system_prompt, user_prompt
