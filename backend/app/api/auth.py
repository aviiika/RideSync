"""Sign-in endpoints.

The password is the registration number, which identifies a student rather
than authenticating one. Endpoints elsewhere in this API are deliberately not
gated on it - see `docs/architecture.md`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.deps import get_auth_service
from app.schemas.auth import IdentityResponse, LoginRequest, SessionResponse
from app.services.auth_service import AuthError, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=SessionResponse)
def login(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> SessionResponse:
    """Sign in with a registration number, using it as the password."""
    try:
        return SessionResponse.from_domain(
            service.login(request.registration_number, request.password)
        )
    except AuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.get("/me", response_model=IdentityResponse)
def me(
    authorization: str | None = Header(default=None),
    service: AuthService = Depends(get_auth_service),
) -> IdentityResponse:
    """Confirm a stored session is still valid, and say whose it is."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue.")

    try:
        registration_number = service.verify(authorization.split(" ", 1)[1].strip())
    except AuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return IdentityResponse(registration_number=registration_number)
