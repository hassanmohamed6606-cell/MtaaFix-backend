import math
import re


CATEGORIES = {
    "Road Damage",
    "Waste Management",
    "Streetlight",
    "Drainage",
    "Water",
    "Public Facility",
    "Other",
}

STATUSES = {"Pending", "In Progress", "Resolved"}

EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$"
)


def validate_registration(data):
    """Validate user registration information."""

    if not isinstance(data, dict):
        return "Registration data must be a JSON object."

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not isinstance(name, str) or not name.strip():
        return "Name is required."

    name = name.strip()

    if len(name) > 100:
        return "Name must not exceed 100 characters."

    if not isinstance(email, str) or not email.strip():
        return "Email is required."

    email = email.strip().lower()

    if len(email) > 255 or not EMAIL_RE.fullmatch(email):
        return "A valid email address is required."

    if not isinstance(password, str) or len(password) < 8:
        return "Password must contain at least 8 characters."

    return None


def validate_report(data, partial=False):
    """Validate report creation and update information."""

    if not isinstance(data, dict):
        return "Report data must be a JSON object."

    required = (
        "title",
        "description",
        "category",
        "location_name",
    )

    if not partial:
        for key in required:
            value = data.get(key)

            if not isinstance(value, str) or not value.strip():
                return (
                    "Title, description, category and location are required."
                )

    if partial and not data:
        return "At least one field must be provided for an update."

    if "title" in data:
        title = data["title"]

        if not isinstance(title, str) or not title.strip():
            return "Title is required."

        if len(title.strip()) > 140:
            return "Title must not exceed 140 characters."

    if "description" in data:
        description = data["description"]

        if not isinstance(description, str) or not description.strip():
            return "Description cannot be empty."

    if "category" in data:
        category = data["category"]

        if not isinstance(category, str) or category not in CATEGORIES:
            return "Invalid category."

    if "location_name" in data:
        location = data["location_name"]

        if not isinstance(location, str) or not location.strip():
            return "Location name cannot be empty."

        if len(location.strip()) > 255:
            return "Location name must not exceed 255 characters."

    if "status" in data:
        status = data["status"]

        if not isinstance(status, str) or status not in STATUSES:
            return "Invalid status."

    coordinate_limits = {
        "latitude": 90,
        "longitude": 180,
    }

    for key, limit in coordinate_limits.items():
        if key not in data or data[key] is None:
            continue

        value = data[key]

        if isinstance(value, bool):
            return f"{key} must be a number."

        try:
            coordinate = float(value)
        except (TypeError, ValueError):
            return f"{key} must be a number."

        if not math.isfinite(coordinate):
            return f"{key} must be a finite number."

        if not -limit <= coordinate <= limit:
            return f"{key} is outside the valid range."

    return None