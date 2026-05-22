---
name: slide-rendering
description: Map each extracted slide-concept entry to one of ~13 slide component types (cover-slide, content-two-col, mcq, mini-game, fill-blank, comparison, timeline, etc.), render the slide as HTML, and assemble the deck. Use this skill in the render + assemble phase of a slides-from-textbook project. Only available when the slides-from-textbook template is active.
metadata:
  triggers:
    - render the slides
    - map to slide components
    - assemble the deck
    - build the HTML
    - slide rendering phase
---

# slide-rendering (slides-from-textbook template)

The 2app side of a slides project. The 2skills half produced per-slide concept entries at `<project>/.claude/skills/`. This skill maps each entry to a slide component, renders an HTML fragment, and assembles them into a single self-contained .html file.

## The component types

Drawn from lesson2slides' 13 components, adapted as needed:

- **cover-slide** — deck title + subtitle. One per deck. First slide.
- **section-divider** — major chapter/section heading. Optional; use sparingly.
- **content-two-col** — text + visual side-by-side. The workhorse component.
- **timeline** — events or steps in temporal order.
- **bar-chart** — comparison of quantities. Inlined SVG.
- **chain-process** — sequential process (A → B → C). Inlined SVG.
- **comparison** — side-by-side comparison of two/three things.
- **fill-blank** — interactive: hide answer, reveal on click. Quiz-style.
- **mcq** — multiple-choice question. Records the click but doesn't gate progression.
- **mini-game** — simple interactive widget (drag-pair, hotspot click, button-pick).
- **canvas-sim** — small canvas-based simulation. Per-domain; usually template-specific assets.
- **web-source** — references external source (link + description). For "learn more."
- **media-embed** — image, audio, or video. Inlined as base64 (no external CDN).

## Picking a component per entry

The chunk's `visual_kind` hint and the entry's `component_type` field (set during extract) propose a component. Verify it fits the actual entry content:

- Entry has a question with options → **mcq**
- Entry has a fact with one true answer → **fill-blank** (hide the answer for student interaction)
- Entry has 2-3 things being compared → **comparison**
- Entry has a sequence of steps → **timeline** or **chain-process**
- Entry has a chart suggestion → **bar-chart** (if quantities) or sketch via SVG
- Entry is dense prose with one image → **content-two-col**
- Entry is summary or recap → use lesson2slides' `summary` style (compact key takeaways)
- Entry needs external context → **web-source** with a vetted link

If the suggested component doesn't fit, pick the closest one and document the override in the rendered HTML's `data-original-suggestion` attribute (useful for the teacher's edit mode).

## Rendering an HTML fragment

Each slide is an HTML `<div class="slide">` with a `data-slide="N"` attribute and component-specific markup inside. Templates and CSS for each component live as embedded `<style>` and JS as embedded `<script>` — the produced deck is a single .html file, no external deps.

The deck shell wraps all slides with:

- A `<head>` with embedded styles + base64-inlined fonts.
- Nav dots at the bottom (one per slide).
- Arrow-key listeners + scripts for game logic, blank reveal, MCQ click handling.
- An edit-mode toggle that activates per-element SVG/text editing for teachers (lesson2slides' v2 editor pattern).

## Inlining media

All images, fonts, audio go in as base64. The produced .html file is self-contained — offline shareable. This means:

- Compress images aggressively (150 DPI JPEG q=85 per lesson2slides' aesthetic).
- Use SVG for charts/diagrams where possible (small + crisp).
- Avoid video unless essential; videos balloon the file size.

For very large decks, the size cap is ~50MB — beyond that, split into multiple decks.

## Assembling the deck

After all per-slide HTML fragments are rendered, the assembler:

1. Strips any LLM-emitted markdown wrappers or `<!DOCTYPE>` repetition.
2. Counts slides by `data-slide="N"` attributes.
3. Injects `{{N_SLIDES}}` and `{{NAV_DOTS}}` placeholders in the shell.
4. Writes the final HTML to `<project>/<app-output>/deck.html`.

The assembler is implemented inline (in the render phase, layer-2 Claude does it via Bash + sed/python). No separate script needed for v1.

## Done criteria for the render phase

- `<project>/<app-output>/deck.html` exists.
- File opens cleanly in a browser (smoke test: `open deck.html` on macOS, eyes-check the first 3 slides).
- Arrow-key navigation works (test by pressing → multiple times; counter at bottom updates).
- No external network calls during render (verify via browser dev tools — no failed CDN loads).
- Total file size ≤ 50MB.

## What this skill does NOT do

- It doesn't extract content. That's [[knowledge-extraction]].
- It doesn't decide chunking boundaries. That's [[chunking]] (this template's override).
- It doesn't auto-fetch media — if the source had image references, the extract phase resolved them. The render phase just inlines what's there.

## Cross-references

- [[chunking]] — produces the chunks the extract phase reads
- [[knowledge-extraction]] — produces the entries this skill renders
- [[app-design-thinking]] — the 2app shape; slide deck = static-output app (Shape 1)
- [[code-quality-guardrails]] — quality checks on the produced .html (no broken refs, no external CDN, smoke test passes)
- [[packaging]] — runs in parallel with rendering for the meta-knowledge (concept entries) that the produced deck consumes
