import hashlib
import hmac


def is_valid_signature(raw_body: bytes, header: str | None, app_secret: str) -> bool:
    """Verifies that the HMAC-SHA256 signature in X-Hub-Signature-256 matches the payload."""
    if not header or not app_secret:
        return False
    if not header.startswith("sha256="):
        return False
    expected_hex = header.removeprefix("sha256=")
    computed_hex = hmac.new(
        key=app_secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(computed_hex, expected_hex)
