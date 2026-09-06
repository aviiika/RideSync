"""Sign-in by registration number.

The rule under test is that the password *is* the registration number. These
tests pin the behaviour, including the parts that are deliberately weak, so
nobody later mistakes this for authentication.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.services.auth_service import AuthError, AuthService

REGISTRATION = "24MID0159"


@pytest.fixture
def auth() -> AuthService:
    return AuthService(secret="test-secret", session_hours=12)


class TestLogin:
    def test_signs_in_when_the_password_is_the_registration_number(
        self, auth: AuthService
    ) -> None:
        session = auth.login(REGISTRATION, REGISTRATION)

        assert session.registration_number == REGISTRATION
        assert session.token
        assert session.expires_at > datetime.now(UTC)

    def test_case_and_spacing_do_not_matter(self, auth: AuthService) -> None:
        session = auth.login("  24mid0159 ", "24Mid0159")
        assert session.registration_number == REGISTRATION

    def test_rejects_a_password_that_is_not_the_registration_number(
        self, auth: AuthService
    ) -> None:
        with pytest.raises(AuthError, match="password is your registration number"):
            auth.login(REGISTRATION, "hunter2")

    @pytest.mark.parametrize(
        "value",
        ["", "24MID", "MID0159", "244MID0159", "24MI0159", "24MID01590", "24-MID-0159"],
    )
    def test_rejects_a_malformed_registration_number(
        self, auth: AuthService, value: str
    ) -> None:
        with pytest.raises(AuthError, match="registration number"):
            auth.login(value, value)

    def test_the_error_explains_the_expected_shape(self, auth: AuthService) -> None:
        with pytest.raises(AuthError, match="24MID0159"):
            auth.login("nonsense", "nonsense")


class TestTokens:
    def test_a_fresh_token_verifies(self, auth: AuthService) -> None:
        token = auth.login(REGISTRATION, REGISTRATION).token
        assert auth.verify(token) == REGISTRATION

    def test_a_tampered_registration_number_is_rejected(self, auth: AuthService) -> None:
        """The whole point of signing: local storage cannot be edited into a session."""
        token = auth.login(REGISTRATION, REGISTRATION).token
        forged = token.replace(REGISTRATION, "24MID9999")

        with pytest.raises(AuthError):
            auth.verify(forged)

    def test_a_tampered_expiry_is_rejected(self, auth: AuthService) -> None:
        registration, expiry, signature = auth.login(REGISTRATION, REGISTRATION).token.split(".")
        extended = f"{registration}.{int(expiry) + 100_000}.{signature}"

        with pytest.raises(AuthError):
            auth.verify(extended)

    def test_a_token_signed_with_another_secret_is_rejected(self, auth: AuthService) -> None:
        other = AuthService(secret="different-secret")
        token = other.login(REGISTRATION, REGISTRATION).token

        with pytest.raises(AuthError):
            auth.verify(token)

    def test_an_expired_token_is_rejected(self) -> None:
        service = AuthService(secret="test-secret", session_hours=1)
        expired = service._sign(REGISTRATION, datetime.now(UTC) - timedelta(seconds=1))

        with pytest.raises(AuthError, match="expired"):
            service.verify(expired)

    @pytest.mark.parametrize("token", ["", "nonsense", "a.b", "a.b.c.d", "24MID0159.notanumber.x"])
    def test_malformed_tokens_are_rejected(self, auth: AuthService, token: str) -> None:
        with pytest.raises(AuthError):
            auth.verify(token)

    def test_a_secret_is_required(self) -> None:
        with pytest.raises(ValueError, match="secret"):
            AuthService(secret="")


class TestLoginEndpoint:
    def test_signs_in(self, client: TestClient) -> None:
        response = client.post(
            "/auth/login",
            json={"registration_number": REGISTRATION, "password": REGISTRATION},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["registration_number"] == REGISTRATION
        assert body["token"]

    def test_a_wrong_password_is_401_with_a_usable_message(self, client: TestClient) -> None:
        response = client.post(
            "/auth/login",
            json={"registration_number": REGISTRATION, "password": "wrong"},
        )

        assert response.status_code == 401
        assert "registration number" in response.json()["detail"]

    def test_a_malformed_number_is_401(self, client: TestClient) -> None:
        response = client.post(
            "/auth/login", json={"registration_number": "abc", "password": "abc"}
        )
        assert response.status_code == 401

    def test_an_empty_request_is_rejected(self, client: TestClient) -> None:
        assert client.post("/auth/login", json={}).status_code == 422

    def test_me_returns_the_signed_in_student(self, client: TestClient) -> None:
        token = client.post(
            "/auth/login",
            json={"registration_number": REGISTRATION, "password": REGISTRATION},
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
