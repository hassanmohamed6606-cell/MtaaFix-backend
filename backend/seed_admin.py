"""Create or promote an administrator: python seed_admin.py name email password"""
import sys
from dotenv import load_dotenv
load_dotenv()
from app import create_app
from app.extensions import db
from app.models import User

if len(sys.argv) != 4:
    raise SystemExit("Usage: python seed_admin.py <name> <email> <password>")
app = create_app()
with app.app_context():
    name, email, password = sys.argv[1], sys.argv[2].lower(), sys.argv[3]
    user = User.query.filter_by(email=email).first() or User(name=name, email=email)
    user.name, user.role = name, "admin"
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    print(f"Administrator ready: {email}")
