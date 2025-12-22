"""
Email generation using OpenAI GPT-4.

This module creates personalized networking emails based on contact
information and configurable prompts.
"""

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from . import prompt_components

# Load environment variables
load_dotenv()

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
    
    Return ONLY valid JSON:
    {{
      "subject": "Brief subject line",
      "body": "The email body starting with 'Hi {first_name},'"
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

        subject = data.get("subject", f"Interest in {company}")
        body_content = data.get("body", f"Hi {first_name},\n\nI'd love to connect.")

        # Build signature
        signature = f"""
Best,
{your_name}
Lead Electrical Engineer | Baylor SAE Baja Racing Team
{your_school} | Rogers School of Engineering
B.S. Electrical & Computer Engineering, Class of 2027
{your_email} | (832) 728-6936
""".strip()

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