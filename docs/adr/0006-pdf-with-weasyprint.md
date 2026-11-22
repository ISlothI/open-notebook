# 0006 – PDF with WeasyPrint

- **Status:** Accepted
- **Date:** 2026-11-22

## Context

Exports need a cover, a table of contents with page numbers, bookmarks and running headers. The content is written by users and rendered on the server.

## Decision

Markdown is converted to HTML with raw HTML disabled, and WeasyPrint renders it with paged-media CSS. Its resource loader is replaced by one that refuses everything, so a document cannot make the server request anything. Fonts are part of the image (Newsreader, OFL; DejaVu).

## Alternatives

| Alternative | Why not |
|---|---|
| Headless Chromium | Several hundred MB in the image, much memory, a large attack surface; page numbers in a table of contents need tricks |
| LaTeX, Typst | Markdown conversion and escaping of user text are harder |

## Consequences

- Images in notes are not printed; their alternative text is.
- The test for outgoing requests was verified by removing the protection: it then fails.
- Rendering is CPU-bound in the worker; a 20-page note collection resulting in a 411 kB file took 9.3 seconds (one measurement).
