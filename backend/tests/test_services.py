from io import BytesIO
from types import SimpleNamespace
from werkzeug.datastructures import FileStorage
from app.services import email_service, image_service


def test_email_service_skips_when_sendgrid_is_not_configured(monkeypatch):
    monkeypatch.delenv("SENDGRID_API_KEY", raising=False)
    monkeypatch.delenv("MAIL_FROM", raising=False)
    assert email_service.send_email("user@example.com", "Subject", "<p>Body</p>") is False

