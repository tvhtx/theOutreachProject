"""
Gmail API integration for sending emails.

This module handles OAuth authentication and email sending via Gmail API.
"""

from __future__ import print_function
import base64
import os
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.environ.get("CREDENTIALS_FILE", os.path.join(BASE_DIR, "credentials.json"))
TOKEN_FILE = os.environ.get("TOKEN_FILE", os.path.join(BASE_DIR, "token.json"))

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def get_gmail_service() -> Any:
    """
    Get an authenticated Gmail API service.
    
    Handles OAuth flow if no valid token exists.
    
    Returns:
        Gmail API service object.
    """
    creds = None

    # Load token.json if it exists
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If there is no valid token, start OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save new token (fixed indentation - was incorrectly nested)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    return service


def create_message(
    sender_name: str,
    sender_email: str,
    to: str,
    subject: str,
    body_text: str,
) -> dict[str, str]:
    """
    Create a Gmail API message object.
    
    Args:
        sender_name: Display name of sender.
        sender_email: Email address of sender.
        to: Recipient email address.
        subject: Email subject line.
        body_text: Plain text body of the email.
    
    Returns:
        Dictionary with 'raw' key containing base64-encoded message.
    """
    message = MIMEText(body_text, "plain", "utf-8")
    message["To"] = to
    message["From"] = formataddr((sender_name, sender_email))
    message["Subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return {"raw": raw}


def send_message(service: Any, user_id: str, message: dict) -> dict:
    """
    Send an email via Gmail API.
    
    Args:
        service: Authenticated Gmail API service.
        user_id: User ID (usually "me" for authenticated user).
        message: Message object from create_message().
    
    Returns:
        API response with sent message details.
    """
    sent = service.users().messages().send(userId=user_id, body=message).execute()
    return sent
