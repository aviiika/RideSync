"""Sign-in wire schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.services.auth_service import Session


class LoginRequest(BaseModel):
    """Sign in with a registration number.

    The password is the registration number. That is identification, not
    security, and the endpoint description says so.
    """

    registration_number: str = Field(min_length=1, max_length=32, examples=["24MID0159"])
    password: str = Field(min_length=1, max_length=32, examples=["24MID0159"])


class SessionResponse(BaseModel):
    """A signed, expiring session token."""

    registration_number: str
    token: str
    expires_at: datetime

    @classmethod
    def from_domain(cls, session: Session) -> SessionResponse:
        return cls(
            registration_number=session.registration_number,
            token=session.token,
            expires_at=session.expires_at,
        )


class IdentityResponse(BaseModel):
    """Who a token belongs to."""

    registration_number: str
