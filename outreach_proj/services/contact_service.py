"""
Contact management service.

Handles CRUD operations for contacts with user scoping.
"""

import csv
from datetime import datetime, timezone
from io import StringIO
from typing import Optional
from sqlalchemy.orm import Session

from ..models import Contact, User


class ContactService:
    """Service for managing contacts."""
    
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
    
    def get_all(
        self, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[str] = None,
        company: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[Contact]:
        """
        Get all contacts for the current user.
        
        Args:
            skip: Number of records to skip (pagination)
            limit: Maximum records to return
            status: Filter by status
            company: Filter by company
            search: Search in name, email, company
        """
        query = self.db.query(Contact).filter(Contact.user_id == self.user.id)
        
        if status:
            query = query.filter(Contact.status == status)
        
        if company:
            query = query.filter(Contact.company.ilike(f"%{company}%"))
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Contact.first_name.ilike(search_term)) |
                (Contact.last_name.ilike(search_term)) |
                (Contact.email.ilike(search_term)) |
                (Contact.company.ilike(search_term))
            )
        
        return query.order_by(Contact.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_count(self) -> int:
        """Get total count of contacts for the current user."""
        return self.db.query(Contact).filter(Contact.user_id == self.user.id).count()
    
    def get_by_id(self, contact_id: int) -> Optional[Contact]:
        """Get a contact by ID (scoped to current user)."""
        return self.db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.user_id == self.user.id
        ).first()
    
    def get_by_email(self, email: str) -> Optional[Contact]:
        """Get a contact by email (scoped to current user)."""
        return self.db.query(Contact).filter(
            Contact.email == email.lower(),
            Contact.user_id == self.user.id
        ).first()
    
    def create(
        self,
        first_name: str,
        last_name: Optional[str] = None,
        email: Optional[str] = None,
        company: Optional[str] = None,
        job_title: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        phone: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        notes: Optional[str] = None,
        custom_fields: Optional[dict] = None,
    ) -> Contact:
        """Create a new contact."""
        contact = Contact(
            user_id=self.user.id,
            first_name=first_name,
            last_name=last_name,
            email=email.lower().strip() if email else None,
            company=company,
            job_title=job_title,
            city=city,
            state=state,
            country=country,
            phone=phone,
            linkedin_url=linkedin_url,
            notes=notes,
            custom_fields=custom_fields,
        )
        self.db.add(contact)
        self.db.flush()
        return contact
    
    def update(self, contact_id: int, **kwargs) -> Optional[Contact]:
        """Update a contact's fields."""
        contact = self.get_by_id(contact_id)
        if not contact:
            return None
        
        for key, value in kwargs.items():
            if hasattr(contact, key) and key not in ('id', 'user_id', 'created_at'):
                if key == 'email' and value:
                    value = value.lower().strip()
                setattr(contact, key, value)
        
        contact.updated_at = datetime.now(timezone.utc)
        self.db.flush()
        return contact
    
    def delete(self, contact_id: int) -> bool:
        """Delete a contact."""
        contact = self.get_by_id(contact_id)
        if not contact:
            return False
        
        self.db.delete(contact)
        self.db.flush()
        return True
    
    def bulk_create(self, contacts_data: list[dict]) -> list[Contact]:
        """Create multiple contacts at once."""
        contacts = []
        for data in contacts_data:
            contact = Contact(
                user_id=self.user.id,
                first_name=data.get('first_name', data.get('firstName', '')),
                last_name=data.get('last_name', data.get('lastName')),
                email=data.get('email', '').lower().strip() if data.get('email') else None,
                company=data.get('company'),
                job_title=data.get('job_title', data.get('jobTitle')),
                city=data.get('city'),
                state=data.get('state'),
                country=data.get('country'),
                phone=data.get('phone'),
                notes=data.get('notes'),
            )
            self.db.add(contact)
            contacts.append(contact)
        
        self.db.flush()
        return contacts
    
    def import_from_csv(self, csv_content: str) -> tuple[int, list[str]]:
        """
        Import contacts from CSV content.
        
        Args:
            csv_content: CSV file content as string
            
        Returns:
            Tuple of (imported_count, error_messages)
        """
        errors = []
        imported = 0
        
        # Handle BOM
        if csv_content.startswith('\ufeff'):
            csv_content = csv_content[1:]
        
        try:
            reader = csv.DictReader(StringIO(csv_content))
            
            for i, row in enumerate(reader, start=2):  # Start at 2 for header row
                # Map common column names
                first_name = (
                    row.get('First Name') or 
                    row.get('first_name') or 
                    row.get('FirstName') or
                    row.get('Name', '').split()[0] if row.get('Name') else ''
                )
                
                if not first_name:
                    errors.append(f"Row {i}: Missing first name")
                    continue
                
                last_name = (
                    row.get('Last Name') or 
                    row.get('last_name') or 
                    row.get('LastName') or
                    (' '.join(row.get('Name', '').split()[1:]) if row.get('Name') else '')
                )
                
                email = (
                    row.get('Email Address') or 
                    row.get('email') or 
                    row.get('Email') or
                    row.get('E-mail')
                )
                
                # Check for duplicate
                if email and self.get_by_email(email):
                    errors.append(f"Row {i}: Email {email} already exists")
                    continue
                
                try:
                    self.create(
                        first_name=first_name.strip(),
                        last_name=last_name.strip() if last_name else None,
                        email=email.strip() if email else None,
                        company=(row.get('Company') or row.get('company') or '').strip() or None,
                        job_title=(row.get('Job Title') or row.get('job_title') or row.get('Title') or '').strip() or None,
                        city=(row.get('Business City') or row.get('city') or row.get('City') or '').strip() or None,
                        state=(row.get('Business State') or row.get('state') or row.get('State') or '').strip() or None,
                        phone=(row.get('Business Phone') or row.get('phone') or row.get('Phone') or '').strip() or None,
                    )
                    imported += 1
                except Exception as e:
                    errors.append(f"Row {i}: {str(e)}")
                    
        except Exception as e:
            errors.append(f"CSV parsing error: {str(e)}")
        
        return imported, errors
    
    def export_to_csv(self) -> str:
        """Export all contacts to CSV format."""
        contacts = self.get_all(limit=10000)
        
        output = StringIO()
        fieldnames = [
            'First Name', 'Last Name', 'Email Address', 'Company', 
            'Job Title', 'City', 'State', 'Phone', 'Status', 'Notes'
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for contact in contacts:
            writer.writerow({
                'First Name': contact.first_name,
                'Last Name': contact.last_name or '',
                'Email Address': contact.email or '',
                'Company': contact.company or '',
                'Job Title': contact.job_title or '',
                'City': contact.city or '',
                'State': contact.state or '',
                'Phone': contact.phone or '',
                'Status': contact.status,
                'Notes': contact.notes or '',
            })
        
        return output.getvalue()
    
    def get_stats(self) -> dict:
        """Get contact statistics for the current user."""
        total = self.get_count()
        
        # Count by status
        from sqlalchemy import func
        status_counts = (
            self.db.query(Contact.status, func.count(Contact.id))
            .filter(Contact.user_id == self.user.id)
            .group_by(Contact.status)
            .all()
        )
        
        stats = {
            'total': total,
            'by_status': {status: count for status, count in status_counts},
        }
        
        # Contacts with email vs without
        with_email = (
            self.db.query(Contact)
            .filter(Contact.user_id == self.user.id, Contact.email.isnot(None), Contact.email != '')
            .count()
        )
        stats['with_email'] = with_email
        stats['without_email'] = total - with_email
        
        return stats
