from app.extensions import db
from app.models import Report, User


def test_user_password_is_hashed_and_verifiable(app):
    with app.app_context():
        user = User(name="Amina", email="amina@example.com")
        user.set_password("CorrectHorse1")
        assert user.password_hash != "CorrectHorse1"
        assert user.check_password("CorrectHorse1")
        assert not user.check_password("wrong-password")

