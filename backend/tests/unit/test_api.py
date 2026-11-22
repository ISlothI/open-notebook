import json
import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine

from open_notebook.bootstrap import build_services
from open_notebook.entrypoints.api.app import create_app
from open_notebook.entrypoints.api.observability import REQUEST_ID_HEADER
from open_notebook.infrastructure.logging import configure_logging
from open_notebook.settings import Settings


class FakeProbe:
    def __init__(self, available: bool) -> None:
        self._available = available

    def is_available(self) -> bool:
        return self._available


def client(available: bool = True) -> TestClient:
    # The engine connects lazily, so these tests never touch a database.
    services = build_services(create_engine("postgresql+psycopg://nobody@127.0.0.1:1/none"))
    app = create_app(FakeProbe(available), services, version="1.2.3")
    return TestClient(app, base_url="https://testserver")


def test_live_reports_version() -> None:
    response = client().get("/api/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.2.3"}


def test_live_does_not_depend_on_database() -> None:
    assert client(available=False).get("/api/health/live").status_code == 200


def test_ready_when_database_answers() -> None:
    assert client().get("/api/health/ready").status_code == 200


def test_not_ready_when_database_is_down() -> None:
    response = client(available=False).get("/api/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"


def test_well_formed_request_id_is_kept() -> None:
    request_id = str(uuid.uuid4())

    response = client().get("/api/health/live", headers={REQUEST_ID_HEADER: request_id})

    assert response.headers[REQUEST_ID_HEADER] == request_id


@pytest.mark.parametrize("supplied", ["short", "x" * 65, "has spaces inside", 'quote"injection'])
def test_unsafe_request_id_is_replaced(supplied: str) -> None:
    response = client().get("/api/health/live", headers={REQUEST_ID_HEADER: supplied})

    assert uuid.UUID(response.headers[REQUEST_ID_HEADER])


def test_unknown_paths_share_one_metric_label() -> None:
    api = client()
    api.get("/api/nope-1")
    api.get("/api/nope-2")

    metrics = api.get("/metrics").text

    assert 'route="unmatched",status="404"' in metrics
    assert "nope-1" not in metrics


def test_request_log_is_json_with_correlation(capsys: pytest.CaptureFixture[str]) -> None:
    settings = Settings(
        environment="test",
        version="1.2.3",
        database_host="h",
        database_name="n",
        database_user="u",
        database_password=SecretStr("not-a-real-password"),
    )
    configure_logging(settings, "api")

    response = client().get("/api/nope")

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    entry = next(line for line in lines if line["event"] == "http_request")
    assert entry["request_id"] == response.headers[REQUEST_ID_HEADER]
    assert entry["service"] == "api"
    assert entry["env"] == "test"
    assert entry["version"] == "1.2.3"
    assert entry["status"] == 404
    assert "ts" in entry


def test_password_does_not_appear_in_settings_repr() -> None:
    settings = Settings(
        database_host="h",
        database_name="n",
        database_user="u",
        database_password=SecretStr("not-a-real-password"),
    )

    assert "not-a-real-password" not in repr(settings)
    assert "not-a-real-password" in settings.database_url


def test_cross_site_changes_are_refused() -> None:
    response = client().post("/api/auth/sign-out", headers={"Origin": "https://evil.example"})

    assert response.status_code == 403
    assert response.json()["code"] == "cross_site_request"


def test_protected_endpoints_need_a_session() -> None:
    response = client().get("/api/items")

    assert response.status_code == 401
    assert response.json()["code"] == "not_signed_in"
