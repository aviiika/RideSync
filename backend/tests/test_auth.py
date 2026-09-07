"""Sign-in.

Any registration number and any password are accepted. These tests pin that
deliberately - including that no password is ever rejected - so nobody later
mistakes this for authentication, and so a real check cannot be removed by
accident once one exists.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.services.auth_service import MAX_REGISTRATION_LENGTH, AuthError, AuthService

REGISTRATION = "24MID0159"


@pytest.fixture
def auth() -> AuthService:
    return AuthService(secret="test-secret", session_hours=12)


class TestLogin:
    def test_signs_in(self, auth: AuthService) -> None:
        session = auth.login(REGISTRATION, "anything")

        assert session.registration_number == REGISTRATION
        assert session.token
        assert session.expires_at > datetime.now(UTC)

    @pytest.mark.parametrize(
        "registration",
        ["24MID0159", "20BCE1234", "21bce9999", "staff-01", "guest", "A", "12345678"],
    )
    def test_accepts_any_registration_number(self, auth: AuthService, registration: str) -> None:
        session = auth.login(registration, "password")
        assert session.registration_number == registration.strip().upper()

    @pytest.mark.parametrize("password", ["x", "password", "24MID0159", "!@#$%^&*()", "   a   "])
    def test_accepts_any_password(self, auth: AuthService, password: str) -> None:
        """No password is ever wrong. Deliberate, and stated everywhere."""
        assert auth.login(REGISTRATION, password).registration_number == REGISTRATION

    def test_case_and_spacing_do_not_matter(self, auth: AuthService) -> None:
        assert auth.login("  24mid0159 ", "pw").registration_number == REGISTRATION

    def test_the_same_person_typed_differently_is_one_identity(self, auth: AuthService) -> None:
        first = auth.login("24mid0159", "a").registration_number
        second = auth.login(" 24MID0159", "b").registration_number
        assert first == second

    @pytest.mark.parametrize("blank", ["", "   ", "\t"])
    def test_an_empty_registration_number_is_refused(self, auth: AuthService, blank: str) -> None:
        with pytest.raises(AuthError, match="Enter your registration number"):
            auth.login(blank, "password")

    @pytest.mark.parametrize("blank", ["", "   "])
    def test_an_empty_password_is_refused(self, auth: AuthService, blank: str) -> None:
        with pytest.raises(AuthError, match="Enter a password"):
            auth.login(REGISTRATION, blank)

    def test_an_absurdly_long_identifier_is_refused(self, auth: AuthService) -> None:
        """Not a security check - a guard against storing nonsense as an identity."""
        with pytest.raises(AuthError, match="too long"):
            auth.login("A" * (MAX_REGISTRATION_LENGTH + 1), "password")


class TestTokens:
    def test_a_fresh_token_verifies(self, auth: AuthService) -> None:
        token = auth.login(REGISTRATION, "pw").token
        assert auth.verify(token) == REGISTRATION

    def test_a_tampered_registration_number_is_rejected(self, auth: AuthService) -> None:
        """The whole point of signing: browser storage cannot be edited into a session."""
        token = auth.login(REGISTRATION, "pw").token
        forged = token.replace(REGISTRATION, "24MID9999")

        with pytest.raises(AuthError):
            auth.verify(forged)

    def test_a_tampered_expiry_is_rejected(self, auth: AuthService) -> None:
        registration, expiry, signature = auth.login(REGISTRATION, "pw").token.split(".")
        extended = f"{registration}.{int(expiry) + 100_000}.{signature}"

        with pytest.raises(AuthError):
            auth.verify(extended)

    def test_a_token_signed_with_another_secret_is_rejected(self, auth: AuthService) -> None:
        other = AuthService(secret="different-secret")

        with pytest.raises(AuthError):
            auth.verify(other.login(REGISTRATION, "pw").token)

    def test_an_expired_token_is_rejected(self) -> None:
        service = AuthService(secret="test-secret", session_hours=1)
        expired = service._sign(REGISTRATION, datetime.now(UTC) - timedelta(seconds=1))

        with pytest.raises(AuthError, match="expired"):
            service.verify(expired)

    @pytest.mark.parametrize("token", ["", "nonsense", "a.b", "24MID0159.notanumber.x"])
    def test_malformed_tokens_are_rejected(self, auth: AuthService, token: str) -> None:
        with pytest.raises(AuthError):
            auth.verify(token)

    def test_an_identifier_containing_a_dot_still_round_trips(self, auth: AuthService) -> None:
        """Identifiers are free text now, so the token format must cope."""
        token = auth.login("first.last", "pw").token
        assert auth.verify(token) == "FIRST.LAST"

    def test_a_secret_is_required(self) -> None:
        with pytest.raises(ValueError, match="secret"):
            AuthService(secret="")


class TestLoginEndpoint:
    def test_signs_in(self, client: TestClient) -> None:
        response = client.post(
            "/auth/login",
            json={"registration_number": REGISTRATION, "password": "whatever"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["registration_number"] == REGISTRATION
        assert body["token"]

    def test_any_password_works(self, client: TestClient) -> None:
        response = client.post(
            "/auth/login",
            json={"registration_number": "20BCE1234", "password": "hunter2"},
        )
        assert response.status_code == 200

    def test_a_blank_registration_number_is_401(self, client: TestClient) -> None:
        response = client.post("/auth/login", json={"registration_number": "   ", "password": "pw"})
        assert response.status_code == 401

    def test_an_empty_request_is_rejected(self, client: TestClient) -> None:
        assert client.post("/auth/login", json={}).status_code == 422

    def test_me_returns_the_signed_in_user(self, client: TestClient) -> None:
        token = client.post(
            "/auth/login",
            json={"registration_number": REGISTRATION, "password": "pw"},
        ).json()["token"]

        response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        assert response.json()["registration_number"] == REGISTRATION

    def test_me_without_a_token_is_401(self, client: TestClient) -> None:
        assert client.get("/auth/me").status_code == 401

    def test_me_with_a_junk_token_is_401(self, client: TestClient) -> None:
        response = client.get("/auth/me", headers={"Authorization": "Bearer nonsense"})
        assert response.status_code == 401

    def test_me_rejects_a_non_bearer_header(self, client: TestClient) -> None:
        response = client.get("/auth/me", headers={"Authorization": "Basic abc"})
        assert response.status_code == 401


def test_shuttle_endpoints_remain_open(client: TestClient) -> None:
    """Documented, not accidental: the sign-in gates the UI, not the API."""
    assert client.get("/shuttles").status_code == 200
    assert client.get("/routes").status_code == 200
