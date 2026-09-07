"""Sign-in.

**There is no authentication here.** Any registration number and any password
are accepted. Sign-in exists so the app knows who to greet and whose settings
to remember - it protects nothing, and every layer says so rather than dressing
it up.

What the module still does properly, because it costs nothing: it normalises
the registration number so the same student is the same identity however they
type it, and it issues a signed, expiring token so a session cannot be forged
or extended by editing browser storage.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

_TOKEN_SEPARATOR = "."

#: Long enough for any real registration number, short enough to reject junk
#: that would only ever be a paste accident.
MAX_REGISTRATION_LENGTH = 32


class AuthError(Exception):
    """Sign-in was refused. The message is safe to show a user."""


@dataclass(frozen=True, slots=True)
class Session:
    """A signed-in user."""

    registration_number: str
    token: str
    expires_at: datetime


class AuthService:
    """Accepts any credentials and issues signed session tokens."""

    def __init__(self, secret: str, session_hours: int = 12) -> None:
        if not secret:
            raise ValueError("an auth secret is required")
        self._secret = secret.encode("utf-8")
        self._session_hours = session_hours

    # ------------------------------------------------------------------ login

    def login(self, registration_number: str, password: str) -> Session:
        """Sign in with any registration number and any password.

        The only refusals are empty fields and an absurdly long identifier -
        neither of which is a security check, just a guard against storing
        nonsense as somebody's identity.
        """
        normalised = normalise_registration_number(registration_number)

        if not normalised:
            raise AuthError("Enter your registration number.")

        if len(normalised) > MAX_REGISTRATION_LENGTH:
            raise AuthError(
                f"That registration number is too long "
                f"(more than {MAX_REGISTRATION_LENGTH} characters)."
            )

        if not password.strip():
            raise AuthError("Enter a password.")

        # The password is not checked against anything. Deliberate: see the
        # module docstring and docs/architecture.md section 14b.

        expires_at = datetime.now(UTC) + timedelta(hours=self._session_hours)
        return Session(
            registration_number=normalised,
            token=self._sign(normalised, expires_at),
            expires_at=expires_at,
        )

    # ----------------------------------------------------------------- verify

    def verify(self, token: str) -> str:
        """Return the registration number a token belongs to.

        Raises :class:`AuthError` if the token is malformed, tampered with, or
        past its expiry.
        """
        try:
            payload, signature = token.rsplit(_TOKEN_SEPARATOR, 1)
            registration_number, expiry_raw = payload.rsplit(_TOKEN_SEPARATOR, 1)
            expires_at = datetime.fromtimestamp(int(expiry_raw), tz=UTC)
        except (ValueError, OverflowError, OSError) as exc:
            raise AuthError("That session is not valid. Please sign in again.") from exc

        if not hmac.compare_digest(signature, self._signature(payload)):
            raise AuthError("That session is not valid. Please sign in again.")

        if expires_at <= datetime.now(UTC):
            raise AuthError("Your session has expired. Please sign in again.")

        return registration_number

    # ---------------------------------------------------------------- signing

    def _sign(self, registration_number: str, expires_at: datetime) -> str:
        payload = f"{registration_number}{_TOKEN_SEPARATOR}{int(expires_at.timestamp())}"
        return f"{payload}{_TOKEN_SEPARATOR}{self._signature(payload)}"

    def _signature(self, payload: str) -> str:
        digest = hmac.new(self._secret, payload.encode("utf-8"), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def normalise_registration_number(value: str) -> str:
    """Upper-case and strip, so 24mid0159 and ' 24MID0159 ' are one identity."""
    return value.strip().upper()
