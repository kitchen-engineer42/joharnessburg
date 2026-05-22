## Active template: slides-from-textbook

This is a slides project. The produced app is a downloadable HTML slide deck (one .html file with base64-inlined media), navigable by arrow keys, with mini-games, MCQ exercises, and optional in-browser edit mode for the teacher.

**Aesthetic discipline** (from lesson2slides DEVLOG): teaching imagery is anti-aesthetic. Restraint, not decoration. Every visual element should teach a concept; if it can't be named "this teaches X," it doesn't belong on the slide. Color palette: 5 semantic colors max; no decorative animation unless the thing itself moves in reality.

**Unit of content**: one slide-worth of knowledge. Chunking targets one-slide-of-content per chunk; the extract phase produces per-slide entries (concept + visual_hint + component_type); the render phase maps entries to one of ~13 component types (cover, content-two-col, mcq, mini-game, fill-blank, etc., per lesson2slides' design).

**Output shape**: single .html file. No external CDN refs (everything inlined for offline shareability). No runtime LLM in the produced deck — the LLM does its work at build time; the deck is static after assembly.
