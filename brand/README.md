# The Agentic Dataset mark

<img src="agentic-dataset-mark-128.png" alt="" width="96" align="right">

A bounded object with one controlled opening. The outer square is the boundary,
the break in its top edge is the single admitted path, and the inner square is
the dataset. It is the whole model in two shapes: **a boundary, and the one way
through it.**

The mark belongs to the **Agentic Dataset** programme, not to this repository
alone. Implementations, papers and packages in the programme use the same mark;
they do not each get their own.

## Files

| | |
|---|---|
| `agentic-dataset-mark.svg` | canonical. Uses `currentColor`, so it inverts for dark backgrounds with no second asset |
| `agentic-dataset-mark-{16,32,48,64,128,256,512}.png` | rasterised, transparent |
| `favicon.ico` | 16/32/48 |
| `agentic-dataset-mark-avatar-1024.png` | the mark on a flat white ground, opaque, for avatars and anywhere transparency or SVG is refused |

## Using it

Two shapes, no text, no gradient, monochrome. Keep it that way.

- Give it clear space of at least the width of the inner square on every side.
- Do not recolour it into a gradient, add an outline, rotate it, or place it on
  a busy background. It inherits text colour; that is the intended mechanism.
- Below about 16 px the opening closes and the mark stops meaning anything.
  Use a word instead.
- The opening is the point. Do not close it, and do not move it to another edge
  — a gap on the right edge reads as the letter C, which is why it is on top.
- Where transparency is not an option — a GitHub avatar composites onto the
  page and a black-on-transparent mark disappears in dark themes — use the
  white-ground raster above. A flat ground is not a recolour: the mark itself
  is unchanged, and it carries the clear space of this section baked in.

## Licensing — read this, it is not the same as the rest of the repository

**The mark is not covered by the CC BY 4.0 licence that covers this
repository's documentation, nor by any other licence in
[`../LICENSE.md`](../LICENSE.md). All rights reserved.**

That is deliberate, and it is the opposite of everything else here. The
specification is CC BY, the vectors are CC0, the conformance software is
Apache-2.0 — all chosen so anyone can implement the contract, commercially or
not, without asking. **An identifier has to work the other way round.** A mark
anyone may modify identifies nothing, and this project specifically may want
"conforms to AD-001 … AD-015" to mean something one day. A freely adaptable
logo would foreclose that.

**You may**, without asking:

- use the unmodified mark to refer to the Agentic Dataset programme, this
  repository, or its packages — in articles, slides, documentation and talks;
- state that your implementation conforms, or does not conform, to the
  specification, in words.

**Please do not**:

- modify the mark, or use it as the identity of your own product, package or
  fork;
- use it in a way implying endorsement of, or affiliation with, an
  implementation that is not part of this programme.

Implementing the contract requires **no permission and no licence** from
anybody. This restriction is about the mark, and only the mark.

Questions: [@doytsujin](https://github.com/doytsujin).
