import os
from io import BytesIO

import cloudinary
import cloudinary.uploader


# Maximum image size: 8 MB
MAX_IMAGE_SIZE = 8 * 1024 * 1024

# Supported image MIME types and their actual file signatures
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
}


class ImageServiceError(RuntimeError):
    """Raised when image validation or upload fails."""


def _get_image_format(image_bytes):
    """
    Identify an image using its file signature.

    This helps prevent users from uploading files that only
    pretend to be images through their MIME type.
    """

    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "jpeg"

    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"

    if (
        image_bytes.startswith(b"RIFF")
        and image_bytes[8:12] == b"WEBP"
    ):
        return "webp"

    return None


def upload_image(file_storage):
    """
    Validate and upload a report image to Cloudinary.

    Args:
        file_storage: A Flask FileStorage object.

    Returns:
        str: Secure Cloudinary image URL.
        None: If no image was provided.

    Raises:
        ImageServiceError: If validation or upload fails.
    """

    # No image is optional.
    if not file_storage or not file_storage.filename:
        return None

    # Check the declared MIME type.
    mime_type = file_storage.mimetype

    if mime_type not in ALLOWED_IMAGE_TYPES:
        raise ImageServiceError(
            "Only JPG, PNG and WEBP images are allowed."
        )

    # Read at most 8 MB + 1 byte to detect oversized files.
    try:
        image_bytes = file_storage.read(MAX_IMAGE_SIZE + 1)
    except Exception as exc:
        raise ImageServiceError(
            "Unable to read the uploaded image."
        ) from exc

    if not image_bytes:
        raise ImageServiceError("The uploaded image is empty.")

    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise ImageServiceError(
            "Image is too large. Maximum size is 8 MB."
        )

    # Verify that the actual file content matches its MIME type.
    actual_format = _get_image_format(image_bytes)
    expected_format = ALLOWED_IMAGE_TYPES[mime_type]

    if actual_format != expected_format:
        raise ImageServiceError(
            "The uploaded file is not a valid "
            "JPG, PNG or WEBP image."
        )

    # Get Cloudinary credentials from environment variables.
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")

    if not all((cloud_name, api_key, api_secret)):
        raise ImageServiceError(
            "Image uploads are not configured. "
            "Add Cloudinary credentials to backend/.env."
        )

    try:
        # Configure Cloudinary.
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )

        # Upload the verified image.
        result = cloudinary.uploader.upload(
            BytesIO(image_bytes),
            folder="mtaafix/reports",
            resource_type="image",
            transformation=[
                {"width": 1600, "crop": "limit"}
            ],
        )

        # Confirm that Cloudinary returned a usable URL.
        if not isinstance(result, dict):
            raise ImageServiceError(
                "Cloudinary returned an invalid response."
            )

        image_url = result.get("secure_url")

        if not isinstance(image_url, str) or not image_url.startswith("https://"):
            raise ImageServiceError(
                "Cloudinary did not return a valid secure image URL."
            )

        return image_url

    except ImageServiceError:
        raise

    except Exception as exc:
        raise ImageServiceError(
            "Cloudinary upload failed. Please try again."
        ) from exc