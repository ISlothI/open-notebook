"""Removes what has outlived its purpose."""

from datetime import timedelta

import structlog

from open_notebook.application.accounts import ATTEMPT_WINDOW
from open_notebook.application.ports import Clock, TransactionFactory

TRASH_RETENTION = timedelta(days=30)
FINISHED_JOB_RETENTION = timedelta(days=7)

log = structlog.get_logger(__name__)


class Cleanup:
    """Safe to run at any time and in several workers at once."""

    def __init__(self, transactions: TransactionFactory, clock: Clock) -> None:
        self._transactions = transactions
        self._clock = clock

    def __call__(self) -> None:
        now = self._clock()
        with self._transactions() as tx:
            removed = {
                "purged_items": tx.housekeeping.purge_trash(now - TRASH_RETENTION),
                "expired_exports": tx.housekeeping.expire_artifacts(now),
                "expired_sessions": tx.housekeeping.delete_sessions(now),
                "old_attempts": tx.housekeeping.delete_failed_logins(now - ATTEMPT_WINDOW),
                "finished_jobs": tx.housekeeping.delete_jobs(now - FINISHED_JOB_RETENTION),
            }
        if any(removed.values()):
            log.info("cleanup_finished", **removed)
