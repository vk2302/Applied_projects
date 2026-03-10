# при поддержке ChatGPT 5.4 Thinking

import secrets
import string

from sqlalchemy.orm import Session

from app.models.link import Link


ALPHABET = string.ascii_letters + string.digits


def generate_short_code(db: Session, length: int = 6) -> str:
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(length))
        exists = db.query(Link).filter(Link.short_code == code).first()
        if not exists:
            return code
