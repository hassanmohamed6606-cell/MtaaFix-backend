import pytest

from app.utils.validators import validate_registration, validate_report


# -------------------------------
# REGISTRATION VALIDATION TESTS
# -------------------------------

def test_registration_accepts_valid_data():
    data = {
        "name": "Amina",
        "email": "amina@example.com",
        "password": "StrongPass123"
    }

    assert validate_registration(data) is None


def test_registration_rejects_missing_name():
    data = {
        "name": "",
        "email": "amina@example.com",
        "password": "StrongPass123"
    }

    assert validate_registration(data) is not None


def test_registration_rejects_long_name():
    data = {
        "name": "A" * 101,
        "email": "amina@example.com",
        "password": "StrongPass123"
    }

    assert validate_registration(data) is not None


def test_registration_rejects_invalid_email():
    data = {
        "name": "Amina",
        "email": "invalid-email",
        "password": "StrongPass123"
    }

    assert validate_registration(data) is not None


def test_registration_rejects_short_password():
    data = {
        "name": "Amina",
        "email": "amina@example.com",
        "password": "123"
    }

    assert validate_registration(data) is not None


def test_registration_rejects_non_string_password():
    data = {
        "name": "Amina",
        "email": "amina@example.com",
        "password": 12345678
    }

    assert validate_registration(data) is not None


def test_registration_rejects_non_dictionary_data():
    assert validate_registration("invalid data") is not None


# -------------------------------
# REPORT VALIDATION TESTS
# -------------------------------

def valid_report():
    return {
        "title": "Pothole near the market",
        "description": "A large pothole needs repair.",
        "category": "Road Damage",
        "location_name": "South B",
        "latitude": -1.2864,
        "longitude": 36.8172
    }


def test_report_accepts_valid_data():
    assert validate_report(valid_report()) is None


def test_report_rejects_missing_required_fields():
    data = {
        "title": "Pothole"
    }

    assert validate_report(data) is not None


def test_report_rejects_empty_title():
    data = valid_report()
    data["title"] = ""

    assert validate_report(data) is not None


def test_report_rejects_long_title():
    data = valid_report()
    data["title"] = "A" * 141

    assert validate_report(data) is not None


def test_report_rejects_empty_description():
    data = valid_report()
    data["description"] = ""

    assert validate_report(data) is not None


def test_report_rejects_invalid_category():
    data = valid_report()
    data["category"] = "Unknown Category"

    assert validate_report(data) is not None


def test_report_rejects_invalid_status():
    data = valid_report()
    data["status"] = "Unknown"

    assert validate_report(data) is not None


def test_report_rejects_empty_location():
    data = valid_report()
    data["location_name"] = ""

    assert validate_report(data) is not None


# -------------------------------
# COORDINATE VALIDATION TESTS
# -------------------------------

@pytest.mark.parametrize(
    "latitude, longitude",
    [
        (-90, -180),
        (90, 180),
        (0, 0),
    ]
)
def test_report_accepts_valid_coordinate_boundaries(latitude, longitude):
    data = valid_report()
    data["latitude"] = latitude
    data["longitude"] = longitude

    assert validate_report(data) is None


@pytest.mark.parametrize(
    "latitude, longitude",
    [
        (91, 36.8),
        (-91, 36.8),
        (-1.2, 181),
        (-1.2, -181),
    ]
)
def test_report_rejects_invalid_coordinates(latitude, longitude):
    data = valid_report()
    data["latitude"] = latitude
    data["longitude"] = longitude

    assert validate_report(data) is not None


def test_report_rejects_non_numeric_coordinates():
    data = valid_report()
    data["latitude"] = "not-a-number"

    assert validate_report(data) is not None


def test_report_rejects_infinite_coordinates():
    data = valid_report()
    data["latitude"] = float("inf")

    assert validate_report(data) is not None


def test_report_rejects_boolean_coordinates():
    data = valid_report()
    data["latitude"] = True

    assert validate_report(data) is not None


# -------------------------------
# PARTIAL UPDATE TESTS
# -------------------------------

def test_report_accepts_valid_partial_update():
    data = {
        "title": "Updated pothole report"
    }

    assert validate_report(data, partial=True) is None


def test_report_rejects_empty_partial_update():
    assert validate_report({}, partial=True) is not None


def test_report_rejects_non_dictionary_data():
    assert validate_report("invalid data") is not None