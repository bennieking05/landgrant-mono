"""Password login and session introspection."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, get_db
from app.db import models
from app.db.models import Persona, User
from app.security.jwt_auth import JWTPrincipal, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=256)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    sub: str
    email: Optional[str] = None
    firm_id: Optional[str] = None
    persona: str
    roles: list[str] = []
    permissions: list[str] = []


def _persona_for_token(user: User) -> Persona:
    if user.persona == Persona.ADMIN:
        return Persona.PLATFORM_ADMIN
    return user.persona


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not _pwd.verify(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    persona = _persona_for_token(user)
    token = create_access_token(
        user_id=user.id,
        email=user.email,
        firm_id=user.firm_id,
        persona=persona,
        roles=[persona.value],
    )
    return LoginResponse(access_token=token)


@router.get("/me", response_model=MeResponse)
def me(
    principal: JWTPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> MeResponse:
    row = db.get(models.User, principal.user_id)
    email = principal.email or (row.email if row else None)
    return MeResponse(
        sub=principal.user_id,
        email=email,
        firm_id=principal.firm_id or (row.firm_id if row else None),
        persona=principal.persona.value,
        roles=list(principal.roles),
        permissions=list(principal.permissions),
    )
