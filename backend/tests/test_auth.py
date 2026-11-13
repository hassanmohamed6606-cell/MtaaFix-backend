def test_register_returns_token_and_user(client):
    response = client.post("/api/auth/register", json={
        "name": "New User", "email": "new@example.com", "password": "StrongPass123"
    })
    assert response.status_code == 201
    assert response.get_json()["user"]["email"] == "new@example.com"
    assert response.get_json()["access_token"]


def test_registration_validates_fields(client):
    response = client.post("/api/auth/register", json={
        "name": "", "email": "not-an-email", "password": "123"
    })
    assert response.status_code == 400


def test_duplicate_email_is_rejected(client):
    data = {"name": "New User", "email": "new@example.com", "password": "StrongPass123"}
    assert client.post("/api/auth/register", json=data).status_code == 201
    assert client.post("/api/auth/register", json=data).status_code == 409


def test_login_rejects_wrong_password(client, resident):
    response = client.post("/api/auth/login", json={
        "email": "resident@example.com", "password": "wrong-password"
    })
    assert response.status_code == 401


def test_me_requires_token_and_returns_user(client, resident_token):
    assert client.get("/api/auth/me").status_code == 401
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {resident_token}"})
    assert response.status_code == 200
    assert response.get_json()["user"]["role"] == "resident"


def test_public_registration_cannot_assign_admin_role(client):
    response = client.post("/api/auth/register", json={
        "name": "Attempted Admin", "email": "attempt@example.com",
        "password": "StrongPass123", "role": "admin"
    })
    assert response.status_code == 201
    assert response.get_json()["user"]["role"] == "resident"