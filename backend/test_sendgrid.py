import logging
import os
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()

# Show SendGrid errors in the terminal
logging.basicConfig(level=logging.INFO)

from app.services.email_service import send_email

# Enter an email address where you can receive mail
recipient = input("Enter your receiving email address: ").strip()

print("Testing MtaaFix SendGrid integration...")

result = send_email(
    recipient,
    "MtaaFix - SendGrid Integration Test",
    """
    <h2>Hello from MtaaFix!</h2>
    <p>Your SendGrid email integration is being tested.</p>
    <p>If you received this email, your backend email service is working!</p>
    <br>
    <strong>MtaaFix Backend Team</strong>
    """
)

if result:
    print("SUCCESS: SendGrid accepted the email!")
else:
    print("FAILED: Email was not accepted. Check the error messages above.")