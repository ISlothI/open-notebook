from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine, text

from open_notebook.application.accounts import MAX_FAILED_ATTEMPTS
from open_notebook.entrypoints.api.session import SESSION_COOKIE
from tests.integration.notebook_client import PASSWORD, NotebookClient

EMAIL = "alice@example.test"


def sign_in(client: NotebookClient, password: str = PASSWORD) -> int:
    response = client.http.post("/api/auth/sign-in", json={"email": EMAIL, "password": password})
    return int(response.status_code)


def test_registration_signs_in(alice: NotebookClient) -> None:
    assert alice.http.get("/api/auth/me").json()["email"] == EMAIL


def test_session_cookie_is_protected(new_client: Callable[[], NotebookClient]) -> None:
    response = new_client().http.post(
        "/api/auth/register", json={"email": EMAIL, "password": PASSWORD}
    )

    cookie = response.headers["set-cookie"].lower()
    assert all(flag in cookie for flag in ("httponly", "secure", "samesite=lax", "path=/"))


def test_sign_in_and_out(alice: NotebookClient, new_client: Callable[[], NotebookClient]) -> None:
    browser = new_client()
    assert sign_in(browser) == 200
    token = browser.http.cookies[SESSION_COOKIE]

    assert browser.http.post("/api/auth/sign-out").status_code == 204

    browser.http.cookies.set(SESSION_COOKIE, token)
    assert browser.http.get("/api/auth/me").status_code == 401
    assert alice.http.get("/api/auth/me").status_code == 200


def test_wrong_password_and_unknown_account_look_the_same(
    alice: NotebookClient, new_client: Callable[[], NotebookClient]
) -> None:
    http = new_client().http
    wrong = http.post("/api/auth/sign-in", json={"email": EMAIL, "password": "wrong password"})
    unknown = http.post("/api/auth/sign-in", json={"email": "x@e.test", "password": PASSWORD})

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_email_can_be_registered_once(
    alice: NotebookClient, new_client: Callable[[], NotebookClient]
) -> None:
    response = new_client().http.post(
        "/api/auth/register", json={"email": EMAIL.upper(), "password": PASSWORD}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "email_taken"


def test_repeated_failures_are_limited(
    alice: NotebookClient, new_client: Callable[[], NotebookClient]
) -> None:
    attacker = new_client()
    for _ in range(MAX_FAILED_ATTEMPTS):
        assert sign_in(attacker, "wrong password") == 401

    assert sign_in(attacker) == 429


def test_successful_sign_in_resets_the_limit(
    alice: NotebookClient, new_client: Callable[[], NotebookClient]
) -> None:
    browser = new_client()
    for _ in range(2):
        for _ in range(MAX_FAILED_ATTEMPTS - 1):
            assert sign_in(browser, "wrong password") == 401
        assert sign_in(browser) == 200


def test_expired_session_is_refused(alice: NotebookClient, engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE sessions SET expires_at = :past"),
            {"past": datetime.now(UTC) - timedelta(seconds=1)},
        )

    assert alice.http.get("/api/auth/me").status_code == 401


def test_secrets_are_not_stored_in_plain_text(alice: NotebookClient, engine: Engine) -> None:
    token = alice.http.cookies[SESSION_COOKIE]
    with engine.connect() as connection:
        stored = connection.execute(
            text("SELECT u.password_hash, s.token_hash FROM users u JOIN sessions s ON true")
        ).one()

    assert stored.password_hash.startswith("$argon2id$")
    assert PASSWORD not in stored.password_hash
    assert bytes(stored.token_hash) != token.encode()
