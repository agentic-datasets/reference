"""Generate the documentation site from the repository's own files.

The site has no content of its own beyond the landing page. Every chapter is a
copy of a file that already exists at the repository root, with its relative
links rewritten for the book's flat layout. That is deliberate: a documentation
site with its own copy of the specification is a second specification, and the
two drift.

    python docs-site/build.py     # regenerate src/
    mdbook build docs-site        # render
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = HERE / "src"
PAGES = HERE / "pages"

# chapter file  <-  repository file
CHAPTERS = {
    "specification.md": "CONFORMANCE.md",
    "portability.md": "docs/PORTABILITY.md",
    "results.md": "docs/RESULTS.md",
    "findings.md": "docs/FINDINGS.md",
    "claims.md": "docs/CLAIMS.md",
    "conformance-package.md": "packages/agentic-dataset-conformance/README.md",
    "authorized-recall.md": "packages/authorized-recall/README.md",
    "contributing.md": "CONTRIBUTING.md",
    "licensing.md": "LICENSE.md",
    "brand.md": "brand/README.md",
    "plan.md": "PLAN.md",
}

GH = "https://github.com/doytsujin/ok-agentic-dataset-reference/blob/main/"
GH_TREE = "https://github.com/doytsujin/ok-agentic-dataset-reference/tree/main/"

# Links that resolve to a chapter of this book.
INTERNAL = {
    "CONFORMANCE.md": "specification.md",
    "docs/PORTABILITY.md": "portability.md",
    "PORTABILITY.md": "portability.md",
    "docs/RESULTS.md": "results.md",
    "RESULTS.md": "results.md",
    "docs/FINDINGS.md": "findings.md",
    "FINDINGS.md": "findings.md",
    "docs/CLAIMS.md": "claims.md",
    "CLAIMS.md": "claims.md",
    "CONTRIBUTING.md": "contributing.md",
    "LICENSE.md": "licensing.md",
    "../LICENSE.md": "licensing.md",
    "PLAN.md": "plan.md",
    "brand/README.md": "brand.md",
    "../packages/authorized-recall/README.md": "authorized-recall.md",
    "packages/authorized-recall/README.md": "authorized-recall.md",
}

LINK = re.compile(r"\]\((?!https?://|#)([^)]+)\)")

# Absolute links back into this repository resolve to a chapter when there is
# one, so the book does not bounce the reader out to GitHub for a page it
# already contains.
ABSOLUTE = re.compile(
    r"\]\(https://github\.com/doytsujin/ok-agentic-dataset-reference/"
    r"(?:blob|tree)/main/([^)#]+)(#[^)]*)?\)"
)


def rewrite(text: str) -> str:
    def sub(m: re.Match) -> str:
        target = m.group(1)
        anchor = ""
        if "#" in target:
            target, anchor = target.split("#", 1)
            anchor = "#" + anchor
        target = target.lstrip("./")
        if target in INTERNAL:
            return f"]({INTERNAL[target]}{anchor})"
        # Everything else points at the repository, so the link still works.
        base = GH_TREE if target.endswith("/") else GH
        return f"]({base}{target}{anchor})"

    def absolute(m: re.Match) -> str:
        target, anchor = m.group(1), m.group(2) or ""
        if target in INTERNAL:
            return f"]({INTERNAL[target]}{anchor})"
        return m.group(0)

    return LINK.sub(sub, ABSOLUTE.sub(absolute, text))


def main() -> None:
    SRC.mkdir(parents=True, exist_ok=True)

    # Hand-authored pages. The mark is inlined as SVG rather than linked as an
    # image so that `currentColor` applies: one asset that is legible on both
    # the light and the dark theme, instead of two PNGs and a media query.
    mark = (ROOT / "brand/agentic-dataset-mark.svg").read_text()
    # Strip the XML comment and flatten to one line before inlining. Its lines
    # are indented four spaces, which Markdown reads as a code block, so the
    # design note would render as visible text above the title.
    mark = re.sub(r"<!--.*?-->", "", mark, flags=re.S)
    mark = " ".join(mark.split())
    mark = mark.replace('width="64" height="64"', 'width="96" height="96"')
    for page in sorted(PAGES.glob("*.md")):
        body = page.read_text().replace("<!-- MARK -->", mark)
        (SRC / page.name).write_text(rewrite(body))
        print(f"  {'pages/' + page.name:<52} -> src/{page.name}")

    for chapter, source in CHAPTERS.items():
        body = (ROOT / source).read_text()
        # The mark is referenced relatively from README-style files.
        body = body.replace('src="agentic-dataset-mark-128.png"',
                            'src="mark.png"')
        (SRC / chapter).write_text(rewrite(body))
        print(f"  {source:<52} -> src/{chapter}")
    shutil.copy(ROOT / "brand/agentic-dataset-mark-256.png", SRC / "mark.png")
    print(f"\n{len(CHAPTERS)} chapters generated, "
          f"{len(list(PAGES.glob('*.md')))} hand-authored pages copied")


if __name__ == "__main__":
    main()
