
import logging
import os
import html

logger = logging.getLogger(__name__)


def send_email(to_email, subject, html_content):
    """Send an email through SendGrid when configured."""

    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("MAIL_FROM")

    if not api_key or not from_email:
        logger.warning("SendGrid not configured; skipped email to %s", to_email)
        return False

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )

        response = SendGridAPIClient(api_key).send(message)

        logger.info("SendGrid response status: %s", response.status_code)

        return 200 <= response.status_code < 300

    except Exception:
        logger.exception("SendGrid email delivery failed")
        return False


def send_welcome_email(user):
    """Send welcome email after successful registration."""

    safe_name = html.escape(str(user.name))

    return send_email(
        user.email,
        "Welcome to MtaaFix",
        f"""
        <h2>Hello {safe_name},</h2>
        <p>Your MtaaFix account is ready.</p>
        <p>Thank you for helping improve your community.</p>
        <br>
        <strong>MtaaFix Team</strong>
        """
    )


def send_login_notification(user):
    """Send notification after successful login."""

    safe_name = html.escape(str(user.name))

    return send_email(
        user.email,
        "New Login to MtaaFix",
        f"""
        <h2>Hello {safe_name},</h2>
        <p>Your MtaaFix account was successfully accessed.</p>
        <p>Thank you for helping improve your community.</p>
        <p>If you do not recognize this login, please contact our support team.</p>
        <br>
        <strong>MtaaFix Security Team</strong>
        """
    )


def send_report_notification(report, event="created"):
    """Send notification when a report is created or updated."""

    safe_name = html.escape(str(report.author.name))
    safe_title = html.escape(str(report.title))
    safe_status = html.escape(str(report.status))
    safe_event = html.escape(str(event))

    return send_email(
        report.author.email,
        f"Your MtaaFix report was {event}",
        f"""
        <h2>Hello {safe_name},</h2>
        <p>Your report <strong>{safe_title}</strong> was {safe_event}.</p>
        <p>Status: {safe_status}</p>
        <br>
        <strong>MtaaFix Team</strong>
        """
    )
