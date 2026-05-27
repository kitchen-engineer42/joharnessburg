# self-correction-echo — the mathlab pattern, generalized

Mathlab's system prompt requires the first or second `op` in its output to be a `text` op echoing back the core equation of the problem. From mathlab's DEVLOG: *"这一步是自我校验"* — *"this step is self-correction."* The model reading its own transcription catches OCR/misread errors before subsequent extraction builds on them.

Generalize: **any skill whose action depends on parsing user-provided content should require an explicit echo of what was understood first.**

## Why it works

LLMs make mistakes on parse-then-act tasks. The mistakes are often invisible: the model misreads a number, then does perfectly competent reasoning on the wrong number. The output looks correct in shape, but it's wrong on substance.

Forcing an explicit echo:

1. **Catches misreading cheaply.** If the echo doesn't match the source, a downstream check flags the chunk for re-processing.
2. **Anchors subsequent reasoning.** Having just typed out "the chunk says X," the model is more likely to extract from X than from a hallucinated X'.
3. **Provides a low-cost audit trail.** Spot-checking echoes is faster than spot-checking extractions.

## Implementation in extraction subagents

The briefing to each subagent includes:

> *"Before extracting any entries from this chunk, emit a `chunk_echo` event with a 2-3 sentence summary of what the chunk says (in your own words). Then proceed with extraction."*

Two events per chunk, minimum: one echo, one or more extraction events. The reducer separates them by `event_type`.

## What the echo should look like

- **Specific enough to verify.** "This chunk discusses regulation X's reporting timeline" is verifiable; "This chunk is about regulations" is not.
- **In the subagent's own words.** Don't quote the chunk verbatim — that proves nothing about whether the model parsed it. A paraphrase shows understanding.
- **Short.** 2-3 sentences. Longer doesn't add signal; it just costs tokens.

## When the echo doesn't match

If a downstream check (manual spot, or a verification subagent) finds an echo that doesn't match the chunk's actual content:

1. Re-extract the chunk (fresh subagent, possibly with stronger model tier or more context).
2. Log the mismatch in PLAN.md's extract phase Log — pattern-of-misreading is signal.
3. If the pattern repeats (e.g., a particular chunk shape consistently misreads), investigate the chunk pipeline upstream — maybe parsing produced bad output, maybe chunking split mid-sentence.

## When echo would be overkill

- Single-chunk extraction where you can manually verify the chunk and result.
- Highly structured chunks (e.g., extracted from a clean database) where there's no reading-comprehension step to mis-execute.

Most knowledge engineering projects benefit from echo. The cost is one cheap event per chunk.

## Origins

This pattern was distilled from the `mathlab` case-generation system prompt — an app whose authors found that asking the model to echo the input before generating output sharply reduced silent misreads. The same self-correction mechanism transfers cleanly to knowledge extraction.
