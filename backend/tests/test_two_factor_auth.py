
import pyotp

from app.extensions import db
from app.models import User


def enable_resident_2fa(client, resident_token):
    headers = {
        "Authorization": f"Bearer {resident_token}"
    }

    setup_response = client.post(
        "/api/auth/2fa/setup",
        headers=headers,
        json={"password": "StrongPass123"},
    )

    assert setup_response.status_code == 200

    secret = setup_response.get_json()["manual_secret"]
    code = pyotp.TOTP(secret).now()

    enable_response = client.post(
        "/api/auth/2fa/enable",
        headers=headers,
        json={"code": code},
    )

    assert enable_response.status_code == 200

    return enable_response.get_json()


def test_resident_can_enroll_in_two_factor_authentication(
    client,
    resident_token,
):
    result = enable_resident_2fa(client, resident_token)

    assert result["user"]["two_factor_enabled"] is True
    assert len(result["recovery_codes"]) == 10
    assert "access_token" not in result


def test_resident_setup_requires_password(
    client,
    resident_token,
):
    response = client.post(
        "/api/auth/2fa/setup",
        headers={
            "Authorization": f"Bearer {resident_token}"
        },
        json={},
    )

    assert response.status_code == 401


def test_resident_login_requires_second_factor_after_enrollment(
    client,
    resident_token,
):
    enable_resident_2fa(client, resident_token)

    response = client.post(
        "/api/auth/login",
        json={
            "email": "resident@example.com",
            "password": "StrongPass123",
        },
    )

    data = response.get_json()

    assert response.status_code == 200
    assert data["mfa_required"] is True
    assert "mfa_token" in data
    assert "access_token" not in data


def test_resident_can_complete_login_with_recovery_code(
    app,
    client,
    resident_token,
):
    enrollment = enable_resident_2fa(client, resident_token)
    recovery_code = enrollment["recovery_codes"][0]

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "resident@example.com",
            "password": "StrongPass123",
        },
    )

    mfa_token = login_response.get_json()["mfa_token"]

    verify_response = client.post(
        "/api/auth/2fa/verify",
        json={
            "mfa_token": mfa_token,
            "code": recovery_code,
        },
    )

    data = verify_response.get_json()

    assert verify_response.status_code == 200
    assert "access_token" in data
    assert data["user"]["two_factor_enabled"] is True


def test_recovery_code_cannot_be_reused(
    client,
    resident_token,
):
    enrollment = enable_resident_2fa(client, resident_token)
    recovery_code = enrollment["recovery_codes"][0]

    first_login = client.post(
        "/api/auth/login",
        json={
            "email": "resident@example.com",
            "password": "StrongPass123",
        },
    )

    first_token = first_login.get_json()["mfa_token"]

    first_verify = client.post(
        "/api/auth/2fa/verify",
        json={
            "mfa_token": first_token,
            "code": recovery_code,
        },
    )

    assert first_verify.status_code == 200

    second_login = client.post(
        "/api/auth/login",
        json={
            "email": "resident@example.com",
            "password": "StrongPass123",
        },
    )

    second_token = second_login.get_json()["mfa_token"]

    second_verify = client.post(
        "/api/auth/2fa/verify",
        json={
            "mfa_token": second_token,
            "code": recovery_code,
        },
    )

    assert second_verify.status_code == 401


def test_invalid_mfa_challenge_is_rejected(
    client,
    resident_token,
):
    enable_resident_2fa(client, resident_token)

    response = client.post(
        "/api/auth/2fa/verify",
        json={
            "mfa_token": "invalid-challenge-token",
            "code": "123456",
        },
    )

    assert response.status_code == 401


def test_resident_can_disable_two_factor_authentication(
    client,
    resident_token,
):
    enable_resident_2fa(client, resident_token)

    response = client.post(
        "/api/auth/2fa/disable",
        headers={
            "Authorization": f"Bearer {resident_token}"
        },
        json={
            "password": "StrongPass123",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["user"]["two_factor_enabled"] is False


def test_admin_must_enroll_before_receiving_access_token(
    app,
    client,
):
    with app.app_context():
        admin = User(
            name="New Admin",
            email="newadmin@example.com",
            role="admin",
        )
        admin.set_password("AdminPass123")

        db.session.add(admin)
        db.session.commit()

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "newadmin@example.com",
            "password": "AdminPass123",
        },
    )

    login_data = login_response.get_json()

    assert login_response.status_code == 200
    assert login_data["mfa_enrollment_required"] is True
    assert "access_token" not in login_data

    enrollment_token = login_data["enrollment_token"]

    setup_response = client.post(
        "/api/auth/2fa/setup",
        json={
            "enrollment_token": enrollment_token,
        },
    )

    assert setup_response.status_code == 200

    secret = setup_response.get_json()["manual_secret"]
    code = pyotp.TOTP(secret).now()

    enable_response = client.post(
        "/api/auth/2fa/enable",
        json={
            "enrollment_token": enrollment_token,
            "code": code,
        },
    )

    enable_data = enable_response.get_json()

    assert enable_response.status_code == 200
    assert enable_data["user"]["two_factor_enabled"] is True
    assert "access_token" in enable_data


def test_admin_cannot_disable_two_factor_authentication(
    client,
    admin_token,
):
    response = client.post(
        "/api/auth/2fa/disable",
        headers={
            "Authorization": f"Bearer {admin_token}"
        },
        json={
            "password": "AdminPass123",
        },
    )

    assert response.status_code == 403
