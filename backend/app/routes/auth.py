
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
)
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.extensions import db
from app.models import User
from app.services.email_service import send_welcome_email
from app.services.two_factor_service import (
    generate_secret,
    encrypt_secret,
    decrypt_secret,
    generate_provisioning_uri,
    verify_totp,
    generate_recovery_codes,
    consume_recovery_code,
)
from app.utils.validators import validate_registration


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

MFA_TOKEN_MAX_AGE = 300


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def get_mfa_serializer():
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"],
        salt="mtaafix-two-factor-auth",
    )


def create_mfa_token(user, purpose):
    return get_mfa_serializer().dumps({
        "user_id": user.id,
        "purpose": purpose,
    })


def read_mfa_token(token, expected_purpose):
    if not token:
        return None

    try:
        payload = get_mfa_serializer().loads(
            token,
            max_age=MFA_TOKEN_MAX_AGE,
        )
    except (BadSignature, SignatureExpired):
        return None

    if payload.get("purpose") != expected_purpose:
        return None

    return payload


def create_user_access_token(user):
    return create_access_token(identity=str(user.id))


def get_user_from_identity():
    identity = get_jwt_identity()

    if not identity:
        return None

    try:
        return db.session.get(User, int(identity))
    except (ValueError, TypeError):
        return None


def verify_user_password(user, password):
    return (
        isinstance(password, str)
        and bool(password)
        and user.check_password(password)
    )


# ---------------------------------------------------------
# REGISTRATION
# ---------------------------------------------------------

@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}

    error = validate_registration(data)

    if error:
        return jsonify(error=error), 400

    email = data["email"].strip().lower()

    if User.query.filter_by(email=email).first():
        return jsonify(
            error="An account with this email already exists."
        ), 409

    user = User(
        name=data["name"].strip(),
        email=email,
        role="resident",
    )

    user.set_password(data["password"])

    db.session.add(user)
    db.session.commit()

    send_welcome_email(user)

    token = create_user_access_token(user)

    return jsonify(
        user=user.to_dict(),
        access_token=token,
    ), 201


# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------

@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}

    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")

    user = User.query.filter_by(email=email).first()

    if not user or not verify_user_password(user, password):
        return jsonify(error="Invalid email or password."), 401

    # Administrators must enroll in 2FA before accessing the system.
    if user.role == "admin" and not user.totp_enabled:
        enrollment_token = create_mfa_token(
            user,
            "admin_enrollment",
        )

        return jsonify(
            message="Two-factor authentication enrollment is required.",
            mfa_enrollment_required=True,
            enrollment_token=enrollment_token,
        ), 200

    # Users who have enabled 2FA must complete verification.
    if user.totp_enabled:
        mfa_token = create_mfa_token(user, "mfa_login")

        return jsonify(
            message="Two-factor authentication is required.",
            mfa_required=True,
            mfa_token=mfa_token,
        ), 200

    # Residents who have not enabled 2FA can log in normally.
    return jsonify(
        user=user.to_dict(),
        access_token=create_user_access_token(user),
    ), 200


# ---------------------------------------------------------
# TWO-FACTOR AUTHENTICATION SETUP
# ---------------------------------------------------------

@auth_bp.post("/2fa/setup")
@jwt_required(optional=True)
def setup_two_factor():
    data = request.get_json(silent=True) or {}

    user = None
    is_admin_enrollment = False

    enrollment_token = data.get("enrollment_token")

    # Administrator enrollment uses a short-lived signed challenge.
    if enrollment_token:
        payload = read_mfa_token(
            enrollment_token,
            "admin_enrollment",
        )

        if not payload:
            return jsonify(error="Invalid or expired enrollment token."), 401

        user = db.session.get(User, payload["user_id"])

        if not user or user.role != "admin":
            return jsonify(error="Administrator account not found."), 404

        is_admin_enrollment = True

    else:
        # Resident enrollment requires an authenticated session.
        user = get_user_from_identity()

        if not user:
            return jsonify(error="Authentication required."), 401

        if user.role == "admin":
            return jsonify(
                error="Administrators must use their enrollment token."
            ), 403

        if not verify_user_password(user, data.get("password")):
            return jsonify(
                error="Your current password is required."
            ), 401

    if user.totp_enabled:
        return jsonify(
            error="Two-factor authentication is already enabled."
        ), 409

    # Generate and encrypt the authenticator secret.
    secret = generate_secret()

    user.totp_secret_encrypted = encrypt_secret(secret)
    user.totp_last_counter = None

    db.session.commit()

    provisioning_uri = generate_provisioning_uri(
        secret,
        user.email,
    )

    return jsonify(
        message="Scan the provisioning URI using your authenticator app.",
        provisioning_uri=provisioning_uri,
        manual_secret=secret,
        enrollment_required=is_admin_enrollment,
    ), 200


# ---------------------------------------------------------
# ENABLE TWO-FACTOR AUTHENTICATION
# ---------------------------------------------------------

@auth_bp.post("/2fa/enable")
@jwt_required(optional=True)
def enable_two_factor():
    data = request.get_json(silent=True) or {}

    user = None
    is_admin_enrollment = False

    enrollment_token = data.get("enrollment_token")

    if enrollment_token:
        payload = read_mfa_token(
            enrollment_token,
            "admin_enrollment",
        )

        if not payload:
            return jsonify(error="Invalid or expired enrollment token."), 401

        user = db.session.get(User, payload["user_id"])

        if not user or user.role != "admin":
            return jsonify(error="Administrator account not found."), 404

        is_admin_enrollment = True

    else:
        user = get_user_from_identity()

        if not user:
            return jsonify(error="Authentication required."), 401

        if user.role == "admin":
            return jsonify(
                error="Administrators must use their enrollment token."
            ), 403

    if user.totp_enabled:
        return jsonify(
            error="Two-factor authentication is already enabled."
        ), 409

    if not user.totp_secret_encrypted:
        return jsonify(
            error="Set up your authenticator before enabling 2FA."
        ), 400

    code = str(data.get("code", "")).strip()

    try:
        secret = decrypt_secret(user.totp_secret_encrypted)
    except ValueError:
        current_app.logger.exception(
            "Unable to decrypt 2FA secret for user %s",
            user.id,
        )
        return jsonify(
            error="Unable to verify authenticator setup."
        ), 500

    matched_counter = verify_totp(
        secret,
        code,
        last_counter=user.totp_last_counter,
    )

    if matched_counter is None:
        return jsonify(
            error="Invalid authenticator code."
        ), 401

    # Generate recovery codes. Their hashes are stored, not plaintext codes.
    recovery_codes, recovery_hashes = generate_recovery_codes()

    user.totp_enabled = True
    user.totp_last_counter = matched_counter
    user.recovery_codes_hashes = recovery_hashes

    db.session.commit()

    response = {
        "message": "Two-factor authentication enabled successfully.",
        "recovery_codes": recovery_codes,
        "warning": (
            "Save these recovery codes somewhere safe. "
            "They will not be shown again."
        ),
        "user": user.to_dict(),
    }

    # Administrators receive their full access token only after enrollment.
    if is_admin_enrollment:
        response["access_token"] = create_user_access_token(user)

    return jsonify(response), 200


# ---------------------------------------------------------
# VERIFY TWO-FACTOR LOGIN
# ---------------------------------------------------------

@auth_bp.post("/2fa/verify")
def verify_two_factor():
    data = request.get_json(silent=True) or {}

    mfa_token = data.get("mfa_token")

    payload = read_mfa_token(mfa_token, "mfa_login")

    if not payload:
        return jsonify(
            error="Invalid or expired authentication challenge."
        ), 401

    user = db.session.get(User, payload["user_id"])

    if not user or not user.totp_enabled:
        return jsonify(
            error="Two-factor authentication is not enabled."
        ), 401

    code = str(data.get("code", "")).strip()

    if not user.totp_secret_encrypted:
        return jsonify(
            error="Authenticator configuration is missing."
        ), 500

    # First try an authenticator code.
    try:
        secret = decrypt_secret(user.totp_secret_encrypted)
    except ValueError:
        current_app.logger.exception(
            "Unable to decrypt 2FA secret for user %s",
            user.id,
        )
        return jsonify(
            error="Unable to verify authentication code."
        ), 500

    matched_counter = verify_totp(
        secret,
        code,
        last_counter=user.totp_last_counter,
    )

    if matched_counter is not None:
        user.totp_last_counter = matched_counter
        db.session.commit()

    else:
        # If it is not a valid TOTP, try a single-use recovery code.
        remaining_hashes = consume_recovery_code(
            code,
            user.recovery_codes_hashes,
        )

        if remaining_hashes is None:
            return jsonify(
                error="Invalid or already-used authentication code."
            ), 401

        user.recovery_codes_hashes = remaining_hashes
        db.session.commit()

    return jsonify(
        message="Authentication successful.",
        user=user.to_dict(),
        access_token=create_user_access_token(user),
    ), 200


# ---------------------------------------------------------
# DISABLE TWO-FACTOR AUTHENTICATION
# ---------------------------------------------------------

@auth_bp.post("/2fa/disable")
@jwt_required()
def disable_two_factor():
    user = get_user_from_identity()

    if not user:
        return jsonify(error="User not found."), 404

    # Administrators cannot disable mandatory 2FA.
    if user.role == "admin":
        return jsonify(
            error="Administrators cannot disable two-factor authentication."
        ), 403

    data = request.get_json(silent=True) or {}

    if not verify_user_password(user, data.get("password")):
        return jsonify(
            error="Your current password is required."
        ), 401

    if not user.totp_enabled:
        return jsonify(
            error="Two-factor authentication is not enabled."
        ), 400

    user.totp_secret_encrypted = None
    user.totp_enabled = False
    user.totp_last_counter = None
    user.recovery_codes_hashes = []

    db.session.commit()

    return jsonify(
        message="Two-factor authentication disabled successfully.",
        user=user.to_dict(),
    ), 200


# ---------------------------------------------------------
# CURRENT USER
# ---------------------------------------------------------

@auth_bp.get("/me")
@jwt_required()
def me():
    user = get_user_from_identity()

    if not user:
        return jsonify(error="User not found."), 404

    return jsonify(user=user.to_dict()), 200
