from uuid import uuid4


def generate_number(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10].upper()}"
