from datetime import datetime, timezone

import pyotp

from app.services.two_factor_service import (
    generate_secret,
    encrypt_secret,
    decrypt_secret,
    generate_provisioning_uri,
    verify_totp,
    generate_recovery_codes,
    consume_recovery_code,
)


def test_secret_encryption_round_trip(app):
    with app.app_context():
        secret = generate_secret()
        encrypted = encrypt_secret(secret)

        assert encrypted != secret
        assert decrypt_secret(encrypted) == secret


def test_provisioning_uri(app):
    with app.app_context():
        secret = generate_secret()
        uri = generate_provisioning_uri(secret, "resident@example.com")

        assert uri.startswith("otpauth://totp/")
        assert "MtaaFix" in uri


def test_totp_verification(app):
    with app.app_context():
        secret = generate_secret()
        totp = pyotp.TOTP(secret)

        counter = totp.timecode(datetime.now(timezone.utc))
        code = totp.generate_otp(counter)

        assert verify_totp(secret, code) == counter


def test_totp_rejects_reused_counter(app):
    with app.app_context():
        secret = generate_secret()
        totp = pyotp.TOTP(secret)

        counter = totp.timecode(datetime.now(timezone.utc))
        code = totp.generate_otp(counter)

        assert verify_totp(secret, code, last_counter=counter) is None


def test_recovery_codes_are_single_use(app):
    with app.app_context():
        codes, hashes = generate_recovery_codes()

        assert len(codes) == 10
        assert len(hashes) == 10

        remaining = consume_recovery_code(codes[0], hashes)

        assert remaining is not None
        assert len(remaining) == 9
        assert consume_recovery_code(codes[0], remaining) is None