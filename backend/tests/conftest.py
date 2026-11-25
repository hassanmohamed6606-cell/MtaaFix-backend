
import pytest
import pyotp

from app import create_app
from app.extensions import db
from app.models import User


@pytest.fixture
def app():
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "JWT_SECRET_KEY": "test-jwt-secret-key-for-testing-only-32-bytes-minimum",
        "SECRET_KEY": "test-secret",
        "TOTP_ENCRYPTION_KEY": "op206wIxqzpPyn0vYXWilP8odbA7DqdASvKIR29CU1E= ",
        "AUTO_CREATE_DB": False,
        "FRONTEND_ORIGIN": "http://localhost:5173",
    })

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def resident(app):
    with app.app_context():
        user = User(
            name="Test Resident",
            email="resident@example.com",
            role="resident",
        )
        user.set_password("StrongPass123")

        db.session.add(user)
        db.session.commit()

        return user.id


@pytest.fixture
def resident_token(client, resident):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "resident@example.com",
            "password": "StrongPass123",
        },
    )

    assert response.status_code == 200
    return response.get_json()["access_token"]


@pytest.fixture
def admin_token(app, client):
    # 1. Create administrator
    with app.app_context():
        admin = User(
            name="Test Admin",
            email="admin@example.com",
            role="admin",
        )
        admin.set_password("AdminPass123")

        db.session.add(admin)
        db.session.commit()

    # 2. Log in
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@example.com",
            "password": "AdminPass123",
        },
    )

    assert login_response.status_code == 200
    login_data = login_response.get_json()

    assert login_data["mfa_enrollment_required"] is True

    enrollment_token = login_data["enrollment_token"]

    # 3. Set up authenticator
    setup_response = client.post(
        "/api/auth/2fa/setup",
        json={
            "enrollment_token": enrollment_token,
        },
    )

    assert setup_response.status_code == 200
    setup_data = setup_response.get_json()

    secret = setup_data["manual_secret"]

    # 4. Generate a valid authenticator code
    code = pyotp.TOTP(secret).now()

    # 5. Complete administrator enrollment
    enable_response = client.post(
        "/api/auth/2fa/enable",
        json={
            "enrollment_token": enrollment_token,
            "code": code,
        },
    )

    assert enable_response.status_code == 200
    enable_data = enable_response.get_json()

    assert enable_data["user"]["two_factor_enabled"] is True

    # 6. Return fully authenticated administrator token
    return enable_data["access_token"]
