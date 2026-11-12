import logging
import os

logger = logging.getLogger(__name__)

def send_email(to_email, subject, html_content):
    """Send an email through SendGrid when configured; otherwise safely skip."""
    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("MAIL_FROM")
    if not api_key or not from_email:
        logger.info("SendGrid not configured; skipped email to %s", to_email)
        return False
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        message = Mail(from_email=from_email, to_emails=to_email,
                       subject=subject, html_content=html_content)
        response = SendGridAPIClient(api_key).send(message)
        return 200 <= response.status_code < 300
    except Exception:
        logger.exception("SendGrid email delivery failed")
        return False

def send_welcome_email(user):
    return send_email(user.email, "Welcome to MtaaFix",
                      f"<p>Hello {user.name},</p><p>Your MtaaFix account is ready. Thank you for helping improve your community.</p>")

