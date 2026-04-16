import base64
import keyword
import secrets


def generate_identifier(used_names: set[str], length: int = 16) -> str:
    """Generate a random Base64-like identifier safe for Python code."""
    import math
    num_bytes = math.ceil(length * 3 / 4)
    while True:
        token = base64.urlsafe_b64encode(secrets.token_bytes(num_bytes)).decode("ascii").rstrip("=")
        candidate = token[:length].replace("-", "a")
        if len(candidate) != length:
            continue
        if candidate[0].isdigit():
            continue
        if keyword.iskeyword(candidate):
            continue
        if not candidate.isidentifier():
            continue
        if candidate in used_names:
            continue
        used_names.add(candidate)
        return candidate
