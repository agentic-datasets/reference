#!/usr/bin/env python3
"""Insert <link rel="canonical"> into the built book, and verify it is there.

The documentation is served from two addresses -- agenticdatasets.org (the
canonical one) and a GitHub Pages mirror -- from a single build. Identical
content at two addresses is a duplicate-content problem, and the visible
cross-link in the pages solves it for a reader but not for a crawler.

mdBook cannot emit these itself: `head.hbs` exposes `{{ path }}` as `index.md`,
not `index.html`, and its templating has no string-replace. So this runs after
`mdbook build`.

    python docs-site/postbuild.py            # insert (idempotent)
    python docs-site/postbuild.py --check    # exit 1 if any page lacks one

**It must be called from every path that builds the book** -- the Makefile's
`docs` target and the Pages workflow both do. That is two callers to keep in
step, which is the cost of having the tag at all; `--check` is what makes the
omission loud instead of silent.
"""

import sys
import pathlib

BASE = "https://agenticdatasets.org/reference/"
BOOK = pathlib.Path(__file__).resolve().parent / "book"

# Not content pages. A 404 should never be canonical to anything, and print.html
# is a concatenation of every other page -- pointing it at itself would assert
# that the duplicate is the original.
SKIP = {"404.html"}
TO_ROOT = {"print.html", "index.html"}

MARK = '<link rel="canonical"'


def canonical_for(rel: str) -> str:
    return BASE if rel in TO_ROOT else BASE + rel


def main() -> int:
    check = "--check" in sys.argv
    if not BOOK.is_dir():
        print(f"error: no built book at {BOOK} -- run `mdbook build docs-site` first",
              file=sys.stderr)
        return 2

    pages = sorted(p for p in BOOK.rglob("*.html"))
    if not pages:
        print(f"error: {BOOK} contains no HTML", file=sys.stderr)
        return 2

    missing, inserted, skipped = [], 0, 0
    for page in pages:
        rel = page.relative_to(BOOK).as_posix()
        if rel in SKIP:
            skipped += 1
            continue
        html = page.read_text(encoding="utf-8")
        if MARK in html:
            continue
        if check:
            missing.append(rel)
            continue
        tag = f'    <link rel="canonical" href="{canonical_for(rel)}">\n'
        # After <head> so it survives whatever mdBook puts in the rest of it.
        i = html.find("<head>")
        if i == -1:
            missing.append(rel)
            continue
        i += len("<head>")
        page.write_text(html[:i] + "\n" + tag + html[i:], encoding="utf-8")
        inserted += 1

    if check:
        if missing:
            print(f"✗ {len(missing)} page(s) without a canonical link:", file=sys.stderr)
            for m in missing[:10]:
                print(f"    {m}", file=sys.stderr)
            print("  run: python docs-site/postbuild.py", file=sys.stderr)
            return 1
        print(f"✓ canonical link present on {len(pages) - skipped} page(s)")
        return 0

    if missing:
        print(f"✗ could not insert into {len(missing)} page(s): {missing[:5]}", file=sys.stderr)
        return 1
    print(f"✓ canonical → {BASE} on {len(pages) - skipped} page(s) "
          f"({inserted} inserted, {len(pages) - skipped - inserted} already present, "
          f"{skipped} skipped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
