"""The use cases, as the entry points receive them."""

from dataclasses import dataclass

from open_notebook.application.accounts import AccountService
from open_notebook.application.library import LibraryService
from open_notebook.application.pages import PageService
from open_notebook.application.search import SearchService


@dataclass(frozen=True)
class Services:
    accounts: AccountService
    library: LibraryService
    pages: PageService
    search: SearchService
