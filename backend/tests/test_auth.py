
import pyotp

from app.extensions import db
from app.models import User


def enable_resident_2fa(client, resident_token):
    """Helper: enroll a resident and return their recovery codes."""
    setup_response = client.post(
        "/api/auth/2fa/setup",
        headers={"Authorization": f"Bearer {resident_token}"},
        json={"password": "StrongPass123"},
    )

    assert setup_response.status_code == 200

    secret = setup_response.get_json()["manual_secret"]
    code = pyotp.TOTP(secret).now()

    enable_response = client.post(
        "/api/auth/2fa/enable",
        headers={"Authorization": f"Bearer {resident_token}"},
        json={"code": code},
    )

    assert enable_response.status_code == 200

    return enable_response.get_json()["recovery_codes"]


# ---------------------------------------------------------
# REGISTRATION TESTS
# ---------------------------------------------------------

def test_register_returns_token_and_user(client):
    response = client.post("/api/auth/register", json={
        "name": "New User",
        "email": "new@example.com",
        "password": "StrongPass123",
    })

    assert response.status_code == 201
    assert response.get_json()["user"]["email"] == "new@example.com"
    assert response.get_json()["access_token"]


def test_registration_validates_fields(client):
    response = client.post("/api/auth/register", json={
        "name": "",
        "email": "not-an-email",
        "password": "123",
    })

    assert response.status_code == 400


def test_duplicate_email_is_rejected(client):
    data = {
        "name": "New User",
        "email": "new@example.com",
        "password": "StrongPass123",
    }

    assert client.post("/api/auth/register", json=data).status_code == 201
    assert client.post("/api/auth/register", json=data).status_code == 409


def test_public_registration_cannot_assign_admin_role(client):
    response = client.post("/api/auth/register", json={
        "name": "Attempted Admin",
        "email": "attempt@example.com",
        "password": "StrongPass123",
        "role": "admin",
    })

    assert response.status_code == 201
    assert response.get_json()["user"]["role"] == "resident"


# ---------------------------------------------------------
# LOGIN TESTS
# ---------------------------------------------------------

def test_login_rejects_wrong_password(client, resident):
    response = client.post("/api/auth/login", json={
        "email": "resident@example.com",
        "password": "wrong-password",
    })

    assert response.status_code == 401


def test_me_requires_token_and_returns_user(client, resident_token):
    assert client.get("/api/auth/me").status_code == 401

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {resident_token}"},
    )

    assert response.status_code == 200
    assert response.get_json()["user"]["role"] == "resident"


def test_admin_login_requires_enrollment(client, app):
    with app.app_context():
        admin = User(
            name="Unenrolled Admin",
            email="unenrolled@example.com",
            role="admin",
        )
        admin.set_password("AdminPass123")

        db.session.add(admin)
        db.session.commit()

    response = client.post("/api/auth/login", json={
        "email": "unenrolled@example.com",
        "password": "AdminPass123",
    })

    data = response.get_json()

    assert response.status_code == 200
    assert data["mfa_enrollment_required"] is True
    assert data["enrollment_token"]
    assert "access_token" not in data


# ---------------------------------------------------------
# RESIDENT TWO-FACTOR ENROLLMENT
# ---------------------------------------------------------

def test_resident_can_enable_two_factor(client, resident_token):
    recovery_codes = enable_resident_2fa(client, resident_token)

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {resident_token}"},
    )

    assert response.status_code == 200
    assert response.get_json()["user"]["two_factor_enabled"] is True
    assert len(recovery_codes) == 10


def test_resident_cannot_enable_with_invalid_code(client, resident_token):
    setup_response = client.post(
        "/api/auth/2fa/setup",
        headers={"Authorization": f"Bearer {resident_token}"},
        json={"password": "StrongPass123"},
    )

    assert setup_response.status_code == 200

    response = client.post(
        "/api/auth/2fa/enable",
        headers={"Authorization": f"Bearer {resident_token}"},
        json={"code": "abcdef"},
    )

    assert response.status_code == 401


def test_resident_setup_requires_correct_password(client, resident_token):
    response = client.post(
        "/api/auth/2fa/setup",
        headers={"Authorization": f"Bearer {resident_token}"},
        json={"password": "wrong-password"},
    )

    assert response.status_code == 401


# ---------------------------------------------------------
# TWO-FACTOR LOGIN AND RECOVERY CODES
# ---------------------------------------------------------

def test_2fa_login_requires_verification(client, resident_token):
    enable_resident_2fa(client, resident_token)

    login_response = client.post("/api/auth/login", json={
        "email": "resident@example.com",
        "password": "StrongPass123",
    })

    data = login_response.get_json()

    assert login_response.status_code == 200
    assert data["mfa_required"] is True
    assert data["mfa_token"]
    assert "access_token" not in data


def test_recovery_code_can_only_be_used_once(client, resident_token):
    recovery_codes = enable_resident_2fa(client, resident_token)
    recovery_code = recovery_codes[0]

    first_login = client.post("/api/auth/login", json={
        "email": "resident@example.com",
        "password": "StrongPass123",
    })

    first_verification = client.post("/api/auth/2fa/verify", json={
        "mfa_token": first_login.get_json()["mfa_token"],
        "code": recovery_code,
    })

    assert first_verification.status_code == 200
    assert first_verification.get_json()["access_token"]

    # Log in again and attempt to reuse the same recovery code.
    second_login = client.post("/api/auth/login", json={
        "email": "resident@example.com",
        "password": "StrongPass123",
    })

    second_verification = client.post("/api/auth/2fa/verify", json={
        "mfa_token": second_login.get_json()["mfa_token"],
        "code": recovery_code,
    })

    assert second_verification.status_code == 401


def test_invalid_mfa_challenge_is_rejected(client):
    response = client.post("/api/auth/2fa/verify", json={
        "mfa_token": "invalid-token",
        "code": "123456",
    })

    assert response.status_code == 401


# ---------------------------------------------------------
# DISABLING TWO-FACTOR AUTHENTICATION
# ---------------------------------------------------------

def test_resident_can_disable_2fa_with_correct_password(
    client,
    resident_token,
):
    enable_resident_2fa(client, resident_token)

    response = client.post(
        "/api/auth/2fa/disable",
        headers={"Authorization": f"Bearer {resident_token}"},
        json={"password": "StrongPass123"},
    )

    assert response.status_code == 200
    assert response.get_json()["user"]["two_factor_enabled"] is False


def test_resident_cannot_disable_2fa_with_wrong_password(
    client,
    resident_token,
):
    enable_resident_2fa(client, resident_token)

    response = client.post(
        "/api/auth/2fa/disable",
        headers={"Authorization": f"Bearer {resident_token}"},
        json={"password": "wrong-password"},
    )

    assert response.status_code == 401


def test_admin_cannot_disable_mandatory_2fa(client, admin_token):
    response = client.post(
        "/api/auth/2fa/disable",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"password": "AdminPass123"},
    )

    assert response.status_code == 403
