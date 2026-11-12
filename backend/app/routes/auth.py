from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from app.extensions import db
from app.models import User
from app.services.email_service import send_welcome_email
from app.utils.validators import validate_registration

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    error = validate_registration(data)
    if error:
        return jsonify(error=error), 400
    email = data["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify(error="An account with this email already exists."), 409
    user = User(name=data["name"].strip(), email=email, role="resident")
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()
    send_welcome_email(user)
    token = create_access_token(identity=str(user.id))
    return jsonify(user=user.to_dict(), access_token=token), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify(error="Invalid email or password."), 401
    return jsonify(user=user.to_dict(), access_token=create_access_token(identity=str(user.id)))


@auth_bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify(error="User not found."), 404
    return jsonify(user=user.to_dict())