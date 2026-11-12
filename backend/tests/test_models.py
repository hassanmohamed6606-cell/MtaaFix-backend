from app.extensions import db
from app.models import Report, User


def test_user_password_is_hashed_and_verifiable(app):
    with app.app_context():
        user = User(name="Amina", email="amina@example.com")
        user.set_password("CorrectHorse1")
        assert user.password_hash != "CorrectHorse1"
        assert user.check_password("CorrectHorse1")
        assert not user.check_password("wrong-password")

def test_report_relationship_and_serialization(app):
    with app.app_context():
        user = User(name="Amina", email="amina@example.com")
        user.set_password("CorrectHorse1")
        db.session.add(user)
        db.session.flush()
        report = Report(title="Pothole", description="Deep pothole", category="Road Damage",
          location_name="South B", user_id=user.id)
        db.session.add(report)
        db.session.commit()
        payload = report.to_dict()
        assert payload["user"]["name"] == "Amina"
        assert payload["status"] == "Pending"
        assert payload["location_name"] == "South B"

                        