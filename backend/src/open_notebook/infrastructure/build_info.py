"""Exposes the running version as a metric, so that releases are visible on dashboards."""

from prometheus_client import Gauge

BUILD_INFO = Gauge("open_notebook_build_info", "Running version", ["service", "version"])


def publish_build_info(service: str, version: str) -> None:
    BUILD_INFO.labels(service=service, version=version).set(1)
