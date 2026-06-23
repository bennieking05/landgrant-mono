"""Regression guard: keep passlib/bcrypt compatible so login never breaks.

passlib 1.7.4 is incompatible with bcrypt>=4.1 — its backend-detection probe
hashes a >72-byte password, which bcrypt>=4.1 rejects with ``ValueError``,
breaking ALL password hashing/verification (``POST /auth/login`` returns 500).

``requirements-dev.txt`` pins ``bcrypt==4.0.1`` for exactly this reason, but a
venv can silently drift (a later ``pip install`` pulling a newer bcrypt). These
tests fail loudly — in CI and locally — if that happens, instead of users
discovering it as a broken login. To fix a failure: ``pip install 'bcrypt==4.0.1'``.
"""

import bcrypt
from passlib.context import CryptContext


def _version_tuple(raw: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in raw.split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        if digits:
            parts.append(int(digits))
    return tuple(parts)


def test_bcrypt_version_compatible_with_passlib() -> None:
    version = getattr(bcrypt, "__version__", "0")
    assert _version_tuple(version) < (4, 1), (
        f"bcrypt {version} is incompatible with passlib 1.7.4 and breaks "
        "password hashing / login. Reinstall the pin: pip install 'bcrypt==4.0.1' "
        "(see backend/requirements-dev.txt)."
    )


def test_password_context_round_trips() -> None:
    # Exercises the exact CryptContext the /auth/login route uses (auth.py).
    # With an incompatible bcrypt this call raises during backend detection.
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = pwd.hash("devpass123")
    assert pwd.verify("devpass123", hashed)
    assert not pwd.verify("wrong-password", hashed)
