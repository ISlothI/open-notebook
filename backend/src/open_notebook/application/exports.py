"""Use cases of PDF export."""

from datetime import timedelta
from uuid import UUID

import structlog

from open_notebook.application.access import require_active_node
from open_notebook.application.jobs import EXPORT_PDF, Job
from open_notebook.application.ports import (
    Clock,
    DocumentRenderer,
    ExportObserver,
    Transaction,
    TransactionFactory,
)
from open_notebook.domain.errors import InvalidValueError, NotFoundError
from open_notebook.domain.exports import (
    Document,
    DocumentPage,
    DocumentSection,
    Export,
    ExportState,
    PageReference,
    Snapshot,
    SnapshotSection,
)
from open_notebook.domain.library import Node, NodeKind

ARTIFACT_LIFETIME = timedelta(hours=24)
MAX_ARTIFACT_BYTES = 25_000_000
PROGRESS_LOADED = 20
PROGRESS_RENDERED = 90

log = structlog.get_logger(__name__)


class ArtifactTooLargeError(Exception):
    pass


class ExportService:
    def __init__(self, transactions: TransactionFactory, clock: Clock) -> None:
        self._transactions = transactions
        self._clock = clock

    def request(self, owner_id: UUID, item_id: UUID) -> Export:
        """Asking again while an export of the same item is under way returns that one."""
        with self._transactions() as tx:
            tx.nodes.lock_tree(owner_id)
            item = require_active_node(tx, owner_id, item_id)
            running = tx.exports.find_unfinished(owner_id, item_id)
            if running:
                return running
            snapshot = self._take_snapshot(tx, owner_id, item)
            export = tx.exports.add(owner_id, item.id, snapshot)
            tx.jobs.enqueue(EXPORT_PDF, {"export_id": str(export.id)})
        log.info("export_requested", export_id=str(export.id), kind=item.kind)
        return export

    def list_exports(self, owner_id: UUID) -> list[Export]:
        with self._transactions() as tx:
            return tx.exports.list_of(owner_id)

    def read(self, owner_id: UUID, export_id: UUID) -> Export:
        with self._transactions() as tx:
            return self._require(tx, owner_id, export_id)

    def download(self, owner_id: UUID, export_id: UUID) -> tuple[Export, bytes]:
        with self._transactions() as tx:
            export = self._require(tx, owner_id, export_id)
            artifact = tx.artifacts.load(export_id)
        is_expired = export.expires_at is not None and export.expires_at <= self._clock()
        if artifact is None or is_expired:
            raise NotFoundError("The file is not available.")
        return export, artifact

    @staticmethod
    def _require(tx: Transaction, owner_id: UUID, export_id: UUID) -> Export:
        export = tx.exports.get(owner_id, export_id)
        if export is None:
            raise NotFoundError("The export does not exist.")
        return export

    def _take_snapshot(self, tx: Transaction, owner_id: UUID, item: Node) -> Snapshot:
        if item.kind is NodeKind.PAGE:
            sections = [SnapshotSection("", [self._reference(tx, item)])]
        elif item.kind is NodeKind.NOTEBOOK:
            active = tx.nodes.list_active(owner_id)
            sections = [
                SnapshotSection(
                    section.title,
                    [self._reference(tx, page) for page in active if page.parent_id == section.id],
                )
                for section in active
                if section.parent_id == item.id
            ]
        else:
            raise InvalidValueError("Only pages and notebooks can be exported.")
        if not any(section.pages for section in sections):
            raise InvalidValueError("There is no page to export.")
        return Snapshot(item.title, self._clock(), sections, item.kind is NodeKind.NOTEBOOK)

    @staticmethod
    def _reference(tx: Transaction, page: Node) -> PageReference:
        return PageReference(page.id, tx.pages.current(page.id).number)


class ExportPdf:
    """Idempotent: a repeated run produces the same document and stores it once."""

    def __init__(
        self,
        transactions: TransactionFactory,
        renderer: DocumentRenderer,
        clock: Clock,
        observer: ExportObserver,
    ) -> None:
        self._transactions = transactions
        self._renderer = renderer
        self._clock = clock
        self._observer = observer

    def __call__(self, job: Job) -> None:
        export_id = UUID(job.payload["export_id"])
        with self._transactions() as tx:
            snapshot = tx.exports.start(export_id)
            if snapshot is None:
                log.info("export_is_gone_or_finished", export_id=str(export_id))
                return
            document = self._load(tx, snapshot)
            tx.exports.report(export_id, PROGRESS_LOADED)

        artifact = self._renderer.render(document)
        if len(artifact) > MAX_ARTIFACT_BYTES:
            raise ArtifactTooLargeError
        with self._transactions() as tx:
            tx.exports.report(export_id, PROGRESS_RENDERED)

        now = self._clock()
        with self._transactions() as tx:
            stored = tx.artifacts.store(export_id, artifact, now + ARTIFACT_LIFETIME)
        if stored:
            self._observer.export_finished(
                ExportState.SUCCEEDED, (now - snapshot.created_at).total_seconds()
            )

    def give_up(self, job: Job) -> None:
        export_id = UUID(job.payload["export_id"])
        with self._transactions() as tx:
            failed = tx.exports.fail(export_id)
        if failed:
            elapsed = self._clock() - failed.created_at
            self._observer.export_finished(ExportState.FAILED, elapsed.total_seconds())

    @staticmethod
    def _load(tx: Transaction, snapshot: Snapshot) -> Document:
        def load_page(reference: PageReference) -> DocumentPage | None:
            version = tx.pages.version(reference.page_id, reference.number)
            return DocumentPage(version.title, version.content) if version else None

        sections = [
            DocumentSection(
                section.title, [page for ref in section.pages if (page := load_page(ref))]
            )
            for section in snapshot.sections
        ]
        return Document(snapshot.title, snapshot.created_at, sections, snapshot.is_notebook)
