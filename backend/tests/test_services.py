from io import BytesIO

import pytest
from werkzeug.datastructures import FileStorage

from app.services.image_service import (
    upload_image,
    ImageServiceError,
    MAX_IMAGE_SIZE,
)


def create_image_file(content, filename="test.jpg", content_type="image/jpeg"):
    return FileStorage(
        stream=BytesIO(content),
        filename=filename,
        content_type=content_type,
    )


# -------------------------------
# BASIC IMAGE VALIDATION TESTS
# -------------------------------

def test_upload_image_returns_none_when_no_image_is_provided():
    assert upload_image(None) is None


def test_upload_image_rejects_unsupported_file_type():
    image = create_image_file(
        b"fake image",
        filename="document.pdf",
        content_type="application/pdf",
    )

    with pytest.raises(ImageServiceError):
        upload_image(image)


def test_upload_image_rejects_empty_file():
    image = create_image_file(b"")

    with pytest.raises(ImageServiceError):
        upload_image(image)


def test_upload_image_rejects_oversized_file():
    image = create_image_file(
        b"\xff\xd8\xff" + b"A" * MAX_IMAGE_SIZE
    )

    with pytest.raises(ImageServiceError):
        upload_image(image)


def test_upload_image_rejects_invalid_image_signature():
    image = create_image_file(
        b"This is not a real image"
    )

    with pytest.raises(ImageServiceError):
        upload_image(image)


def test_upload_image_rejects_mismatched_image_type():
    image = create_image_file(
        b"\x89PNG\r\n\x1a\n" + b"fake image data",
        content_type="image/jpeg",
    )

    with pytest.raises(ImageServiceError):
        upload_image(image)


# -------------------------------
# CLOUDINARY CONFIGURATION TESTS
# -------------------------------

def test_upload_image_rejects_missing_cloudinary_credentials(monkeypatch):
    monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
    monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)

    image = create_image_file(
        b"\xff\xd8\xff" + b"valid image data"
    )

    with pytest.raises(ImageServiceError):
        upload_image(image)


# -------------------------------
# CLOUDINARY UPLOAD TESTS
# -------------------------------

def test_upload_image_returns_secure_url(monkeypatch):
    from app.services import image_service

    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "test-cloud")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "test-key")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "test-secret")

    monkeypatch.setattr(
        image_service.cloudinary.uploader,
        "upload",
        lambda *args, **kwargs: {
            "secure_url": "https://example.com/test-image.jpg"
        },
    )

    image = create_image_file(
        b"\xff\xd8\xff" + b"valid image data"
    )

    result = upload_image(image)

    assert result == "https://example.com/test-image.jpg"


def test_upload_image_rejects_invalid_cloudinary_response(monkeypatch):
    from app.services import image_service

    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "test-cloud")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "test-key")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "test-secret")

    monkeypatch.setattr(
        image_service.cloudinary.uploader,
        "upload",
        lambda *args, **kwargs: {},
    )

    image = create_image_file(
        b"\xff\xd8\xff" + b"valid image data"
    )

    with pytest.raises(ImageServiceError):
        upload_image(image)


def test_upload_image_handles_cloudinary_failure(monkeypatch):
    from app.services import image_service

    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "test-cloud")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "test-key")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "test-secret")

    def failed_upload(*args, **kwargs):
        raise Exception("Cloudinary connection failed")

    monkeypatch.setattr(
        image_service.cloudinary.uploader,
        "upload",
        failed_upload,
    )

    image = create_image_file(
        b"\xff\xd8\xff" + b"valid image data"
    )

    with pytest.raises(ImageServiceError):
        upload_image(image)