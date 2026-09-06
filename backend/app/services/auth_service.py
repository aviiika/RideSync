"""Sign-in by registration number.

**This is identification, not security.** The password is the registration
number itself, so anyone who knows a classmate's number can sign in as them.
That is a deliberate product decision for a campus demo - it personalises the
app without a password anyone has to remember - and it is stated plainly here,
in the API docs and in `docs/architecture.md` rather than dressed up.

What the module does do properly: it validates the registration number's shape,
normalises it, and issues a signed, expiring token so a session cannot be
forged or extended by editing local storage.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

#: VIT registration numbers look like 24MID0159: year, programme, serial.
REGISTRATION_PATTERN = re.compile(r"^\d{2}[A-Za-z]{3}\d{4}$")

_TOKEN_SEPARATOR = "."


class AuthError(Exception):
    """Sign-in was refused. The message is safe to show a user."""


@dataclass(frozen=True, slots=True)
class Session:
    """A signed-in student."""

    registration_number: str
    token: str
    expires_at: datetime


class AuthService:
    """Validates registration numbers and issues signed session tokens."""

    def __init__(self, secret: str, session_hours: int = 12) -> None:
        if not secret:
            raise ValueError("an auth secret is required")
        self._secret = secret.encode("utf-8")
        self._session_hours = session_hours

    # ------------------------------------------------------------------ login

    def login(self, registration_number: str, password: str) -> Session:
        """Sign in, or raise :class:`AuthError` with a usable message."""
        normalised = normalise_registration_number(registration_number)

        if not REGISTRATION_PATTERN.match(normalised):
            raise AuthError(
                "That does not look like a registration number. "
                "It should be two digits, three letters and four digits, like 24MID0159."
            )

        # The password is the registration number. Compared in constant time
        # anyway, so the shape of this check does not change if the rule does.
        if not hmac.compare_digest(normalised, normalise_registration_number(password)):
            raise AuthError("Your password is your registration number.")

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
            registration_number, expiry_raw = payload.split(_TOKEN_SEPARATOR)
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
    """Upper-case and strip, so 24mid0159 and ' 24MID0159 ' are the same person."""
    return value.strip().upper()
