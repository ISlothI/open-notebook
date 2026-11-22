"""Prometheus metrics of background work."""

from collections.abc import Iterator

from prometheus_client import Counter, Histogram
from prometheus_client.core import GaugeMetricFamily, Metric
from prometheus_client.registry import Collector
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from open_notebook.domain.exports import ExportState

JOBS = Counter("jobs", "Finished job executions", ["kind", "outcome"])
INDEX_LAG = Histogram(
    "search_index_lag_seconds",
    "Time from saving a page until it is searchable",
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60, 120, 300, 900),
)

EXPORTS = Counter("exports", "Finished exports", ["state"])
EXPORT_DURATION = Histogram(
    "export_duration_seconds",
    "Time from requesting an export until it is finished",
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60, 120, 300),
)

QUEUE_STATE = text("""
    SELECT kind, state, count(*) AS jobs,
           coalesce(extract(epoch FROM now() - min(created_at)), 0) AS oldest_seconds
    FROM jobs WHERE state <> 'succeeded' GROUP BY kind, state
""")


class JobMetrics:
    def finished(self, kind: str, outcome: str) -> None:
        JOBS.labels(kind, outcome).inc()


class IndexingMetrics:
    def indexed(self, lag_seconds: float) -> None:
        INDEX_LAG.observe(lag_seconds)


class ExportMetrics:
    def export_finished(self, state: ExportState, seconds: float) -> None:
        EXPORTS.labels(state).inc()
        if state is ExportState.SUCCEEDED:
            EXPORT_DURATION.observe(seconds)


class QueueCollector(Collector):
    """Reads the queue at scrape time, so the numbers are true for all workers together."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def collect(self) -> Iterator[Metric]:
        depth = GaugeMetricFamily("job_queue_depth", "Unfinished jobs", labels=["kind", "state"])
        age = GaugeMetricFamily(
            "job_queue_oldest_seconds", "Age of the oldest job", labels=["kind", "state"]
        )
        try:
            with self._engine.connect() as connection:
                for row in connection.execute(QUEUE_STATE):
                    depth.add_metric([row.kind, row.state], row.jobs)
                    age.add_metric([row.kind, row.state], float(row.oldest_seconds))
        except SQLAlchemyError:
            # Missing samples are more honest than zeros during a database outage.
            return
        yield depth
        yield age
