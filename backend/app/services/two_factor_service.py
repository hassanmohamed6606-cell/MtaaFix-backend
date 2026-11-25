
import hashlib
import secrets
from datetime import datetime, timezone

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app


def _fernet():
    key = current_app.config.get("TOTP_ENCRYPTION_KEY")

    if not key:
        raise RuntimeError("TOTP_ENCRYPTION_KEY is not configured.")

    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("TOTP_ENCRYPTION_KEY is invalid.") from exc


def generate_secret():
    return pyotp.random_base32()


def encrypt_secret(secret):
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_secret(encrypted_secret):
    try:
        return _fernet().decrypt(encrypted_secret.encode()).decode()
    except (InvalidToken, ValueError, TypeError) as exc:
        raise ValueError("Unable to decrypt authenticator secret.") from exc


def generate_provisioning_uri(secret, email):
    return pyotp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name="MtaaFix",
    )


def verify_totp(secret, code, last_counter=None):
    if not isinstance(code, str) or not code.isdigit() or len(code) != 6:
        return None

    totp = pyotp.TOTP(secret)
    current_counter = totp.timecode(datetime.now(timezone.utc))

    for counter in (current_counter, current_counter - 1):
        if counter < 0:
            continue

        if last_counter is not None and counter <= last_counter:
            continue

        if secrets.compare_digest(totp.generate_otp(counter), code):
            return counter

    return None


def generate_recovery_codes(count=10):
    codes = [secrets.token_hex(5).upper() for _ in range(count)]
    hashes = [hashlib.sha256(code.encode()).hexdigest() for code in codes]
    return codes, hashes


def consume_recovery_code(code, stored_hashes):
    if not isinstance(code, str):
        return None

    candidate = hashlib.sha256(code.strip().upper().encode()).hexdigest()
    remaining = list(stored_hashes or [])

    for index, stored_hash in enumerate(remaining):
        if secrets.compare_digest(candidate, stored_hash):
            remaining.pop(index)
            return remaining

    return None
