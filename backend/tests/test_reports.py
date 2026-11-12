from app.extensions import db
from app.models import Report


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def payload(title="Pothole near market"):
    return {"title": title, "description": "A deep pothole affecting traffic.",
            "category": "Road Damage", "location_name": "South B, Nairobi",
            "latitude": -1.31, "longitude": 36.82}


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_create_report_requires_auth(client):
    assert client.post("/api/reports", json=payload()).status_code == 401


def test_create_and_read_report(client, resident_token, monkeypatch):
    monkeypatch.setattr("app.routes.reports.send_report_notification", lambda *args: True)
    created = client.post("/api/reports", json=payload(), headers=auth(resident_token))
    assert created.status_code == 201
    report_id = created.get_json()["report"]["id"]
    fetched = client.get(f"/api/reports/{report_id}")
    assert fetched.status_code == 200
    assert fetched.get_json()["report"]["title"] == "Pothole near market"


def test_create_report_validates_required_fields(client, resident_token):
    response = client.post("/api/reports", json={"title": "Missing fields"}, headers=auth(resident_token))
    assert response.status_code == 400


def test_list_reports_filters_and_paginates(client, resident_token, monkeypatch):
    monkeypatch.setattr("app.routes.reports.send_report_notification", lambda *args: True)
    for title, category in [("Pothole", "Road Damage"), ("Overflowing bins", "Waste Management")]:
        data = payload(title)
        data["category"] = category
        client.post("/api/reports", json=data, headers=auth(resident_token))
    response = client.get("/api/reports?category=Road%20Damage&page=1&per_page=1")
    assert response.status_code == 200
    assert len(response.get_json()["reports"]) == 1
    assert response.get_json()["pagination"]["total"] == 1


def test_owner_can_update_and_delete_report(client, resident_token, monkeypatch):
    monkeypatch.setattr("app.routes.reports.send_report_notification", lambda *args: True)
    created = client.post("/api/reports", json=payload(), headers=auth(resident_token)).get_json()["report"]
    updated = client.put(f"/api/reports/{created['id']}", json={"title": "Updated pothole"}, headers=auth(resident_token))
    assert updated.status_code == 200
    assert updated.get_json()["report"]["title"] == "Updated pothole"
    deleted = client.delete(f"/api/reports/{created['id']}", headers=auth(resident_token))
    assert deleted.status_code == 200


def test_other_resident_cannot_edit_or_delete_report(client, app, resident_token, monkeypatch):
    monkeypatch.setattr("app.routes.reports.send_report_notification", lambda *args: True)
    created = client.post("/api/reports", json=payload(), headers=auth(resident_token)).get_json()["report"]
    other = client.post("/api/auth/register", json={"name": "Other", "email": "other@example.com", "password": "StrongPass123"}).get_json()["access_token"]
    assert client.put(f"/api/reports/{created['id']}", json={"title": "Hack"}, headers=auth(other)).status_code == 403
    assert client.delete(f"/api/reports/{created['id']}", headers=auth(other)).status_code == 403


def test_only_admin_can_change_report_status(client, resident_token, admin_token, monkeypatch):
    monkeypatch.setattr("app.routes.reports.send_report_notification", lambda *args: True)
    created = client.post("/api/reports", json=payload(), headers=auth(resident_token)).get_json()["report"]
    path = f"/api/reports/{created['id']}/status"
    assert client.patch(path, json={"status": "Resolved"}, headers=auth(resident_token)).status_code == 403
    response = client.patch(path, json={"status": "Resolved"}, headers=auth(admin_token))
    assert response.status_code == 200
    assert response.get_json()["report"]["status"] == "Resolved"


def test_my_reports_returns_only_current_users(client, resident_token, monkeypatch):
    monkeypatch.setattr("app.routes.reports.send_report_notification", lambda *args: True)
    client.post("/api/reports", json=payload(), headers=auth(resident_token))
    response = client.get("/api/reports/mine", headers=auth(resident_token))
    assert response.status_code == 200
    assert len(response.get_json()["reports"]) == 1


def test_missing_report_returns_404(client):
    assert client.get("/api/reports/9999").status_code == 404


def test_create_report_with_cloudinary_image(client, resident_token, monkeypatch):
    from io import BytesIO
    monkeypatch.setattr("app.routes.reports.upload_image", lambda image: "https://cdn.example/report.jpg")
    data = payload()
    data["image"] = (BytesIO(b"fake-image"), "report.jpg")
    response = client.post("/api/reports", data=data, headers=auth(resident_token), content_type="multipart/form-data")
    assert response.status_code == 201
    assert response.get_json()["report"]["image_url"] == "https://cdn.example/report.jpg"