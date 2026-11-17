import secrets

# Без o, O и 0 — их легко перепутать при ручном вводе.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz123456789"
CODE_PREFIX = "EX-"
CODE_BODY_LENGTH = 8


def generate_join_code() -> str:
    body = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_BODY_LENGTH))
    return f"{CODE_PREFIX}{body}"
