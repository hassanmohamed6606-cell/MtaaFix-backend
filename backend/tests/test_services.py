from io import BytesIO
from types import SimpleNamespace
from werkzeug.datastructures import FileStorage
from app.services import email_service, image_service


def test_email_service_skips_when_sendgrid_is_not_configured(monkeypatch):
    monkeypatch.delenv("SENDGRID_API_KEY", raising=False)
    monkeypatch.delenv("MAIL_FROM", raising=False)
    assert email_service.send_email("user@example.com", "Subject", "<p>Body</p>") is False

def test_image_upload_requires_cloudinary_configuration(monkeypatch):
    for key in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"):
        monkeypatch.delenv(key, raising=False)
    image = FileStorage(stream=BytesIO(b"fake image"), filename="issue.png", content_type="image/png")
    try:
        image_service.upload_image(image)
        assert False, "Expected ImageServiceError"
    except image_service.ImageServiceError as exc:
        assert "not configured" in str(exc)


def test_image_upload_rejects_non_image_mimetype(monkeypatch):
    for key, value in (("CLOUDINARY_CLOUD_NAME", "cloud"), ("CLOUDINARY_API_KEY", "key"), ("CLOUDINARY_API_SECRET", "secret")):
        monkeypatch.setenv(key, value)
    image = FileStorage(stream=BytesIO(b"text"), filename="issue.txt", content_type="text/plain")
    try:
        image_service.upload_image(image)
        assert False, "Expected ImageServiceError"
    except image_service.ImageServiceError as exc:
        assert "Only JPG" in str(exc)


def test_cloudinary_upload_returns_secure_url(monkeypatch):
    for key, value in (("CLOUDINARY_CLOUD_NAME", "cloud"), ("CLOUDINARY_API_KEY", "key"), ("CLOUDINARY_API_SECRET", "secret")):
        monkeypatch.setenv(key, value)
    import cloudinary
    import cloudinary.uploader
    monkeypatch.setattr(cloudinary.uploader, "upload", lambda *args, **kwargs: {"secure_url": "https://cdn.example/image.jpg"})
    image = FileStorage(stream=BytesIO(b"fake image"), filename="issue.jpg", content_type="image/jpeg")
    assert image_service.upload_image(image) == "https://cdn.example/image.jpg"

