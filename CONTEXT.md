# John (joharnessburg)

John is a Claude Code harness for building **knowledge-dense apps**: it wraps a long-running Claude Code session with skills, hooks, slash commands, and a small toolkit so Claude can take unstructured input through knowledge engineering and app building in one session. This glossary is the project's canonical language — when a word here conflicts with a word in older prose, this file wins.

## Language

### The product

**Knowledge-dense app**:
An app that runs a fixed mechanism over many uniform knowledge entries — the mechanism comes from the template (or is designed in the app phases), the entries come from the corpus. If an input doesn't yield an entry population, John is the wrong tool.
_Avoid_: AI app, LLM app

**Entry knowledge**:
The hundreds-to-thousands of parallel, uniform entries extracted from the corpus. Becomes the app's *content*; what the vertical axis fans out over.
_Avoid_: content knowledge, the data

**Mechanism knowledge**:
The meta knowledge of how the app works on its entries — the user's flow, the input→output main line. Few cases; comes from the template (or app-phase design), not from the corpus. Entry and mechanism knowledge differ in source, cardinality, and axis — never run them through one extraction pipeline.
_Avoid_: meta knowledge, app knowledge

### The two halves

**Knowledge phase(s)**:
The first half of a John run — knowledge engineering: parse, chunk, design the schema, extract, rewrite, package. Produces the project's deliverable skills.
_Avoid_: 2skills, the extraction half, knowledge engineering half (as a name)

**App phase(s)**:
The second half — software engineering: design the app mechanism, scaffold, wire mechanics, seed content from the packaged knowledge, polish, deploy.
_Avoid_: 2app, the app building half (as a name)

### The app-type definition

**App-type definition**:
The four decisions that together define how to build a certain type of knowledge-dense app. Once all four are settled, an app type (and hence a template) is *defined*. Two pairs: the knowledge pair describes the material; the app pair describes the machine. In both pairs, *format = what it is / how it works; schema = what it has / how it is built.*
_Avoid_: the four structures

**Knowledge format**:
What kinds of knowledge the corpus holds — rules, stories, concepts, procedures, wiki, screenplays… (The knowledge's *format*: what it is.)
_Avoid_: format of knowledge (word order)

**Knowledge schema**:
What one entry contains — the structured-knowledge-unit shape: fields, links, progressive-disclosure layout. (The knowledge's *schema*: what it has.)
_Avoid_: SKU schema, schema of knowledge (word order)

**App mechanism**:
How the finished app runs over the entries — the user flow, the input→output main line. (The app's *format*: how it works.) This is where mechanism knowledge lands.
_Avoid_: runtime structure, function structure of app, app runtime model

**Build pipeline**:
How this type of app gets built — the phase design of the app phases. (The app's *schema*: how it is built.)
_Avoid_: production pipeline, building pipeline of app

### The working shape

**Horizontal axis**:
The phase sequence (knowledge phases then app phases), advanced one phase at a time by the ralph-loop.

**Vertical axis**:
The parallel knowledge entries within a phase — similar tasks fanned out to subagents or a dynamic workflow, coordinated through the event log.

**Endurance mode**:
A long-running John session with an endurance goal set (`/john:endurance <goal>`); the goal is pinned to the system prompt and survives context compaction. In endurance mode John assumes its configured capabilities (e.g. dynamic workflows) are available and does not pause to re-confirm configuration.

**workerLLM**:
A cheap LLM a *produced app* calls at its own runtime (not Claude in the build session, not a subagent). Reached through any OpenAI-compatible endpoint at `$JOHN_LLM_CLIENT_URL`.
_Avoid_: sub-worker

**Runtime job**:
A background task inside a *produced app* that its end-users wait on (upload → queued → staged generation → progress → download), managed through a persistent task registry and a bounded worker pool — the `job-runtime` skill teaches the pattern. Distinct from build-time vertical-axis work (subagents/workflows in the John session) and from John's own endurance sessions.
_Avoid_: long-running task (ambiguous with John's own long sessions)

### Skill evolution

**Evolution ring(s)**:
The blast-radius levels at which John's text assets evolve, with automation decreasing as the ring rises: Ring 0 = this project (lessons, local override drafts, the worker-skill training loop); Ring 1 = a template (its owner evolves it from accumulated run reports); Ring 2 = John core + the authoring methodology (human-driven analysis only; the top gate is permanently human). Influence travels upward as evidence, never downward as automatic edits.
_Avoid_: levels/layers (collides with John's L1/L2/L3 layer vocabulary)

**Lessons ledger**:
`<project>/.john/lessons/` — append-only, immutable, per-lesson JSON files: condition + lesson + evidence pointers + a scope guess (project/template/core). Written at phase boundaries; the project-local fast store that feeds the rings above.

**Run manifest**:
The provenance a run carries so its evidence is attributable: John version (stamped into workspace.json at init), template name+version, corpus identity, configuration. No manifest, no attribution.

**Process scorecard**:
The deterministic, read-only, frozen-rubric report (`scripts/process_scorecard.py`) of how a run *behaved*: per-phase events and fan-out, gate runs and verdicts, skill invocations, lessons, silent skips. The process-quality signal for everything above the template ring; its rubric is amendable by maintainers only — no automated edit surface can change what it counts.

**Run report**:
The shareable postmortem artifact of one run: scorecard + manifest + outcome summary + candidate lessons, **scrubbed of corpus content** before it leaves the project. The input format of template evolution; shared manually — never transmitted automatically.

**Promotion**:
A lesson crossing a ring boundary (project → template → core), always through scrub-and-generalize: restated so it carries no corpus content and would hold for the next corpus of the domain.
