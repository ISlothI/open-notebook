"""Structured JSON logging to stdout, shared by every process."""

import logging
import sys

import structlog

from open_notebook.settings import ProcessSettings


def configure_logging(settings: ProcessSettings, service: str) -> None:
    def add_service_fields(
        _logger: structlog.typing.WrappedLogger,
        _method: str,
        event: structlog.typing.EventDict,
    ) -> structlog.typing.EventDict:
        event["service"] = service
        event["env"] = settings.environment
        event["version"] = settings.version
        return event

    shared: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
        add_service_fields,
        structlog.processors.dict_tracebacks,
    ]
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level)
    # Logs every request of the client at INFO, which duplicates our own events.
    logging.getLogger("httpx2").setLevel(logging.WARNING)
