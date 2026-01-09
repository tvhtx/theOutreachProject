"""
Email generation using OpenAI GPT-4.

This module creates personalized networking emails based on contact
information and configurable prompts.
"""

import json
import logging
import os
import sys
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

# Handle both direct script execution and package import
_current_dir = os.path.dirname(os.path.abspath(__file__))
if __package__ is None or __package__ == "":
    _parent_dir = os.path.dirname(_current_dir)
    if _parent_dir not in sys.path:
        sys.path.insert(0, _parent_dir)
    from outreach_proj import prompt_components
else:
    from . import prompt_components

# Load environment variables from the package directory
load_dotenv(os.path.join(_current_dir, ".env"))

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Company-specific context for better personalization
COMPANY_CONTEXT_MAP: dict[str, str] = {
    "Arc Boat Co": "high-performance electric boats and marine systems",
    "Scout Motors": "rugged all-electric trucks and SUVs, reviving the classic Scout brand",
    "Apple": "consumer electronics, hardware integration, and high-volume manufacturing",
    "Stark Future": "high-performance electric motocross bikes",
    "Tesla": "electric vehicles and sustainable energy systems",
    "Goldman Sachs": (
        "quantitative trading, software engineering, complex risk analysis "
        "and market making systems engineering"
    ),
}


def generate_personalized_email(
    contact: dict[str, str],
    config: dict[str, Any],
) -> tuple[str, str]:
    """
    Generate a personalized networking email for a contact.
    
    Args:
        contact: Dictionary with contact info (First Name, Company, Job Title, etc.)
        config: Configuration with sender info (your_name, your_email, etc.)
    
    Returns:
        Tuple of (subject, body) for the generated email.
    """
    # Extract contact info with safe defaults
    first_name = contact.get("First Name", "").strip() or "there"
    company = contact.get("Company", "").strip() or "your company"
    title = contact.get("Job Title", "").strip() or "your role"

    # Get industry context
    industry_context = COMPANY_CONTEXT_MAP.get(
        company, "innovative engineering and technology"
    )

    # Extract sender info
    your_name = config.get("your_name", "Taylor Van Horn")
    your_email = config.get("your_email", "")
    your_school = config.get("your_school", "Baylor University")

    prompt = f"""
    You are an expert career coach helping an Electrical & Computer Engineering student network for internships.
    
    **THE SENDER:**
    Name: {your_name}
    Role: Electrical and Computer Engineering student at {your_school}.
    
    **THE RECIPIENT:**
    Job Title: {title}
    Company: {company}
    Context: {industry_context}

    **SKILL ARSENAL:**
    {prompt_components.SKILL_ARSENAL}

    **EXPERIENCE FRAGMENTS:**
    {prompt_components.EXPERIENCE_FRAGMENTS}

    **TASK:**
    Write a short networking email (max 125 words).
    1. Analyze the job title ({title}).
    2. Pick ONE relevant skill that fits this specific role.
    3. Connect the most relevant experience to their company context ({industry_context}).
    
    **SUBJECT LINE GUIDELINES:**
    Create a natural, grammatically correct subject line. Examples of GOOD subjects:
    - "Interest in the Software Engineering role at {company}"
    - "Quick question about data engineering at {company}"
    - "Curious about your engineering work at {company}"
    - "Student interested in the {title} role"
    
    BAD subjects (never use these patterns):
    - "Interest in Senior Software Engineer at {company}" (missing "the" and "role")
    - "Interest in {title}" (sounds robotic)
    
    **IMPORTANT:** Do NOT include any closing signature (like "Best," "Thanks," "Sincerely," etc.) or your name at the end. The signature will be added automatically.
    
    Return ONLY valid JSON:
    {{
      "subject": "Natural, grammatically correct subject line",
      "body": "The email body starting with 'Hi {first_name},' - DO NOT include a signature or closing"
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You return ONLY valid JSON objects."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Empty response from OpenAI")
        
        content = content.strip()

        # Clean markdown code fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        data = json.loads(content)

        # Handle list response (AI sometimes returns [{...}] instead of {...})
        if isinstance(data, list):
            data = data[0] if data else {}

        subject = data.get("subject", f"Interest in opportunities at {company}")
        body_content = data.get("body", f"Hi {first_name},\n\nI'd love to connect.")

        # Build signature from config (with fallbacks for backwards compatibility)
        your_title = config.get("your_title", "")
        your_department = config.get("your_department", "")
        your_phone = config.get("your_phone", "")
        graduation_year = config.get("graduation_year", "")
        
        # Build signature lines dynamically
        signature_lines = ["Best,", your_name]
        
        if your_title:
            signature_lines.append(your_title)
        
        if your_school or your_department:
            school_line = " | ".join(filter(None, [your_school, your_department]))
            signature_lines.append(school_line)
        
        if your_school and config.get("your_major"):
            degree_line = f"B.S. {config.get('your_major')}"
            if graduation_year:
                degree_line += f", Class of {graduation_year}"
            signature_lines.append(degree_line)
        
        contact_parts = [p for p in [your_email, your_phone] if p]
        if contact_parts:
            signature_lines.append(" | ".join(contact_parts))
        
        signature = "\n".join(signature_lines)

        full_body = f"{body_content}\n\n{signature}"
        return subject, full_body

    except Exception as e:
        logger.error(f"Error generating email for {company}: {e}")
        
        # Return fallback so the campaign continues
        fallback_body = (
            f"Hi {first_name},\n\n"
            f"I am an ECE student at {your_school} interested in {company}. "
            f"I'd love to learn more about your work as a {title}.\n\n"
            f"Best,\n{your_name}"
        )
        return f"Student interested in {company}", fallback_body