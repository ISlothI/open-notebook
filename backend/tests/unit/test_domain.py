import pytest

from open_notebook.domain.accounts import ensure_password, normalise_email
from open_notebook.domain.errors import InvalidHierarchyError, InvalidValueError
from open_notebook.domain.library import MAX_TITLE_LENGTH, NodeKind, clean_title, ensure_placement
from open_notebook.domain.pages import MAX_CONTENT_BYTES, clean_content

FOLDER, NOTEBOOK, SECTION, PAGE = NodeKind
VALID_PLACEMENTS = {
    (FOLDER, None),
    (FOLDER, FOLDER),
    (NOTEBOOK, None),
    (NOTEBOOK, FOLDER),
    (SECTION, NOTEBOOK),
    (PAGE, SECTION),
}


@pytest.mark.parametrize("kind", NodeKind)
@pytest.mark.parametrize("parent", [None, *NodeKind])
def test_placement_rules(kind: NodeKind, parent: NodeKind | None) -> None:
    if (kind, parent) in VALID_PLACEMENTS:
        ensure_placement(kind, parent)
    else:
        with pytest.raises(InvalidHierarchyError):
            ensure_placement(kind, parent)


def test_title_whitespace_is_normalised() -> None:
    assert clean_title("  My \n first\t page ") == "My first page"


@pytest.mark.parametrize("title", ["", "   ", "x" * (MAX_TITLE_LENGTH + 1)])
def test_invalid_titles(title: str) -> None:
    with pytest.raises(InvalidValueError):
        clean_title(title)


def test_line_endings_are_normalised() -> None:
    assert clean_content("a\r\nb\n") == "a\nb\n"


@pytest.mark.parametrize("content", ["a\x00b", "é" * (MAX_CONTENT_BYTES // 2 + 1)])
def test_invalid_content(content: str) -> None:
    with pytest.raises(InvalidValueError):
        clean_content(content)


def test_email_is_normalised() -> None:
    assert normalise_email(" Alice@Example.Test ") == "alice@example.test"


@pytest.mark.parametrize(
    "email", ["", "alice", "alice@", "a b@example.test", "a@b", "x" * 250 + "@e.test"]
)
def test_invalid_emails(email: str) -> None:
    with pytest.raises(InvalidValueError):
        normalise_email(email)


@pytest.mark.parametrize("password", ["", "x" * 9, "x" * 129])
def test_invalid_passwords(password: str) -> None:
    with pytest.raises(InvalidValueError):
        ensure_password(password)
