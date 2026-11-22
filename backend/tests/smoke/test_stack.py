"""Checks the running stack from outside, through the proxy and verified TLS."""

import os
import ssl
from collections.abc import Iterator

import httpx2
import pytest


@pytest.fixture
def http() -> Iterator[httpx2.Client]:
    tls = ssl.create_default_context(cafile=os.environ["SMOKE_CA_FILE"])
    with httpx2.Client(base_url=os.environ["SMOKE_BASE_URL"], verify=tls, timeout=10) as client:
        yield client


def test_api_is_ready_down_to_the_database(http: httpx2.Client) -> None:
    response = http.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"]


def test_web_application_is_served(http: httpx2.Client) -> None:
    response = http.get("/")

    assert response.status_code == 200
    assert "<title>Open Notebook</title>" in response.text


def test_metrics_are_not_public(http: httpx2.Client) -> None:
    assert "http_requests_total" not in http.get("/metrics").text
