from collections.abc import Generator
from fastapi import Depends, Header, HTTPException, status

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.db.models import Persona, User


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_persona(x_persona: str = Header(..., alias="X-Persona")) -> Persona:
    try:
        return Persona(x_persona)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid persona header") from exc


def get_current_user(persona: Persona = Depends(get_current_persona)) -> User:
    # Placeholder stub until SSO integration wired. Returns pseudo-user object.
    return User(id="stub", email="stub@example.com", persona=persona, full_name="Stub User")
