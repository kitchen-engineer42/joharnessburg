# runtime-vs-buildtime-llm — where LLMs live in the produced app

A central design decision for any John-produced app: does the LLM run at **build time** (once, when the app is being constructed) or at **runtime** (every time an end-user interacts with the deployed app)? Both modes work; they have different cost, capability, and architectural implications.

## Build-time LLM

The LLM runs while John is producing the app. Each invocation is **one-off** — happens once during the pipeline, never repeats per user.

**Examples from the subsites:**

- lesson2slides: gpt-5.4 generates slide content during build; the deployed slide deck has no runtime LLM.
- create-any-portfolio: Code Agent generates the Next.js site during build; the published portfolio has no runtime LLM (except an optional chatbot).
- mystery-detective-game: case generation happens once when a new case is requested (effectively build-time per-case).

**Implications:**

- **Costs are one-off.** You can afford SOTA models (Claude Opus, GPT-5.5) because each generation runs once.
- **Output can be heavyweight.** Build-time LLMs can produce structured plans, multi-step reasoning, long-form content.
- **Errors are recoverable.** If the build LLM makes a mistake, you re-run it before shipping. End-users don't see failures.
- **Declarative output is fine.** You can let the model produce free-form JSON/markdown/code; downstream tooling parses it.

## Runtime LLM

The LLM runs every time the end-user does something. Each invocation is **per-user** — scales with traffic, costs per-call.

**Examples:**

- mystery-detective-game: NPC dialogue per user-turn during play.
- mathlab: ops generation per problem the user pastes.
- create-any-portfolio: optional chatbot answers questions about the portfolio owner.

**Implications:**

- **Costs are per-user.** SOTA models become expensive at scale. Use workerLLMs (SiliconFlow, DeepSeek per `.env`; templates wire these). Reserve SOTA for the cases where it's genuinely needed.
- **Latency matters.** A 30s response time is fine at build; not at runtime. Streaming, partial results, optimistic UI.
- **Errors are user-facing.** When a runtime LLM fails, the end-user sees it. Need fallbacks (mathlab uses local rule-based JSON when the API returns 5xx).
- **Imperative DSLs beat declarative prose.** Per spec §8.13: "When working with these [weaker workerLLM] models, be more imperative and less declarative." mathlab's `ops` DSL is small, each op self-contained, each step builds on the last. The model is much better at this than at producing a free-form game-state JSON.

## Choosing

Decide based on the runtime structure (the third of the four structures):

- **Static output, no per-user variation** → build-time only. (slide deck, portfolio, vote page.)
- **Per-user input that's predictable but content-creative** → build-time, with per-input caching. (Generated slide deck *per uploaded textbook* — each is a build, but each build is once.)
- **Per-user input where every interaction is unique** → runtime LLM. (Chat, game dialogue, ad-hoc analysis.)
- **Pure runtime decisions with no LLM judgment needed** → no LLM at all. (Voting, polling, simple CRUD.)

## Both at once

Many real apps have both:

- Build-time generates the static structure (rules, scenes, characters, slide layouts).
- Runtime invokes a workerLLM for per-user adaptation (apply rules to user input, role-play characters, generate quiz questions from slide content).

The clean line between them is a design decision. Default: maximize build-time work (cheaper, more deterministic), minimize runtime work (expensive, error-prone).

## Source

Pattern synthesized from the 5 subsites in `/Users/mac/Desktop/john/subsites/` on the dev machine plus spec §8.3 (worker LLM tier per task) and §8.13 (imperative DSL principle from mathlab).
