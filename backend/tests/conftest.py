import pytest
from app import create_app
from app.extensions import db
from app.models import User


@pytest.fixture
def app():
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "JWT_SECRET_KEY": "test-jwt-secret",
        "SECRET_KEY": "test-secret",
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
        user = User(name="Test Resident", email="resident@example.com", role="resident")
        user.set_password("StrongPass123")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def resident_token(client, resident):
    response = client.post("/api/auth/login", json={
        "email": "resident@example.com", "password": "StrongPass123"
    })
    return response.get_json()["access_token"]


@pytest.fixture
def admin_token(app, client):
    with app.app_context():
        admin = User(name="Test Admin", email="admin@example.com", role="admin")
        admin.set_password("AdminPass123")
        db.session.add(admin)
        db.session.commit()
    response = client.post("/api/auth/login", json={
        "email": "admin@example.com", "password": "AdminPass123"
    })
    return response.get_json()["access_token"]
