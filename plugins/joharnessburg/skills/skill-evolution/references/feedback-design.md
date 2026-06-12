# Feedback-collection design — a decision you make, not a setting you inherit

Evolution runs on feedback, and *where the feedback comes from* is a per-project design decision. John teaches the decision space and the rubric; the template (if one is loaded) supplies the domain's instantiation — a template built for evolution declares its feedback design and ships its scorer or eval set. Your job is then instantiation, not invention. No template guidance? Design it explicitly and record the design in PLAN.md so the gate is auditable.

## The design space

Two independent choices, crossed:

**Collection point** — where the signal is captured:

| Point | What you get | Cost | Latency |
|---|---|---|---|
| **Build session** (eval during the John run) | scores on a held-out slice; immediately usable by the training loop | tokens now | fast — drives the loop |
| **App runtime** (instrument the produced app) | real outcomes on real use, accumulating after ship | engineering once | slow — feeds the *next* cycle |
| **Post-deployment human feedback** | corrections/judgments from the app's actual users | someone's time | slowest, highest-value |

**Ground truth** — who decides what's correct:

| Source | Strength | Weakness |
|---|---|---|
| **Corpus-derived labels** (the corpus self-labels: known answers, gold annotations, parallel text) | free, plentiful | only covers what the corpus states |
| **Programmatic verifier** (schema conformance, executable checks, exact match) | deterministic, ungameable | only covers checkable properties |
| **SOTA-model judge** | flexible, cheap-ish | gameable by optimization pressure; drifts |
| **Human domain expert** | the real ground truth | scarce, slow — spend on calibration, not per-item |

Two kinds of feedback exist and a mature design uses **both**:

1. **Results of the app at runtime** — judged by the app's *end users*, who are fully capable of it: the domain expert using a verification app already knows the rules and can correct it; a game's player knows whether it's fun. This is the gold signal.
2. **Quality of the build process** — judged by people with software/knowledge-engineering experience (a build that packaged everything for release before testing anything is wrong *regardless of the output*). End users can't provide this; the process scorecard captures its deterministic floor, and experienced reviewers the rest.

## The rubric

1. **Pick the cheapest signal whose Goodhart risk you can bound.** A programmatic verifier beats an LLM judge wherever both apply; a corpus label beats both.
2. **Never optimize against a lone LLM judge.** When a judge is unavoidable, (a) make it a *verifying* judge — check grounding, citations, conformance of the worker's claim — rather than one that re-does the task and compares; verification is harder to game than generation. (b) Calibrate it periodically against a small ground-truth sample (expert labels), and stop trusting it when calibration drifts.
3. **Don't score skill text by how it reads.** Measured result worth memorizing: blind frontier-model judgments of "which skill document is better" perform at chance, and prose qualities — clarity, completeness, structure, tone — have zero predictive value. The three properties that *do* predict a skill's utility:
   - **failure-mechanism encoding** — the text names *why* the worker fails and gives executable remedies;
   - **actionable specificity** — step-level procedures referencing the domain's concrete objects;
   - **a high-risk action blacklist** — explicit "never do X" for known damaging moves.
   Use these three as a *generation-time* checklist when drafting or editing skills (that's where they measurably help); don't use any text-quality judgment as an acceptance gate — only scores are gates.
4. **Declare the design in PLAN.md** (one short block: collection points, ground truth, calibration plan). Auditable beats clever.

## Worked example: a document-verification app

(The shape of the doc-verification example template; adapt the specifics.)

The app's workers check documents against extracted rules — verification with citations. A sound two-loop design:

- **Fast loop (build session):** hold out a slice of the corpus where outcomes are known (the regulation states the rule; the sample document visibly complies or violates). Score each worker verdict two ways: a *programmatic* layer (did it cite a real clause? does the output conform to the rule schema?) and a *verifying judge* (is the cited clause actually about the claimed obligation — grounding, not re-verification). This is cheap enough to drive the training loop within the build.
- **Slow gold (app runtime):** the app's end users are domain experts — every correction they make in the running app is a ground-truth label. Instrument the app to keep its corrections (locally, the user's data); those corrections recalibrate the fast loop's judge and, summarized and scrubbed, flow back to the template owner as run-report evidence for the *template's* next version.

The trap this design avoids: scoring verification quality with a single LLM judge that re-judges the document. Under training pressure the worker drifts toward verdicts the judge likes — confident phrasing, fewer checkable citations — while real accuracy is flat or worse. Verifying judges + periodic expert calibration close that hole.

## Minimal designs that are still legitimate

- **No scorer exists and can't cheaply be built** (taste-driven domains: "is this slide beautiful", "is this game fun"): then there is no training loop — collect end-user reactions as lessons, let the template owner aggregate them, and keep the deterministic floor (conformance checks, the process scorecard) as the only automated signal. Declaring "no automated scorer; human-reaction lessons only" in PLAN.md is a valid design.
- **Corpus labels only**: fine — many knowledge-engineering domains self-label. State the coverage limit (what the labels can't see) in the design block.
