# common-guardrails — four categories, with examples

The categories below are starting points — NOT a closed checklist. Templates extend per their domain. Pick what applies to the project's produced-app shape.

## Security

**What can go wrong**: leaked credentials, exposed user data, injection vulnerabilities, permissive defaults.

**Patterns to check**:

- API keys / tokens in committed code (`grep -rE 'sk-[A-Za-z0-9]{40,}|api[_-]?key\s*=\s*["'"'"']\w+'`)
- Hardcoded production URLs (`grep -rE 'https://.*\.prod\.|https://api\.openai\.com|YOUR_API_HERE'`)
- Permissive CORS (`Access-Control-Allow-Origin: \*` in production configs)
- Unescaped user input rendered as HTML (template engines: check `{{ var }}` vs `{{ var | safe }}` or `<%- %>` vs `<%= %>`)
- Default passwords / secrets in templates (`admin/admin`, `password123`, `secret`)
- Permissive file system access (paths read from user input without sandboxing)

**Auto-fix**: rarely safe. Most security issues need user confirmation (the "leaked key" might be a placeholder; the hardcoded URL might be intentional for testing).

## Code quality

**What can go wrong**: produced code doesn't run, doesn't build, fails import, has obvious mistakes.

**Patterns to check**:

- Imports declared but module not in dependencies (parse imports, diff against `package.json`/`requirements.txt`/`Cargo.toml`)
- Broken import paths (run `python -c "import x"` or `node -e "require('x')"` for each)
- Lint errors at the "error" level (not warnings — those generate noise)
- Type errors (if TypeScript / mypy / etc.)
- Syntax errors (`python -m py_compile`, `node --check`)
- Unused imports (warnings only — sometimes intentional; flag, don't auto-fix)

**Auto-fix**: often safe. Missing deps → add to manifest. Broken import path → grep for the right path. Syntax errors → usually require the LLM to understand intent.

## UX

**What can go wrong**: app technically works but is hostile to use.

**Patterns to check**:

- Error states unhandled (no `catch` on async calls, no fallback rendering when API returns null)
- Infinite spinners (state machines that have a "loading" state but no error/timeout path)
- Debug noise in production (`console.log`, `print()`, `dbg!()` — pattern depends on language)
- Placeholder text not replaced (`Lorem ipsum`, `TODO: replace`, `Your text here`)
- Hardcoded test data (`testUser`, `mock@example.com`)

**Auto-fix**: partial. Console.log removal is usually safe; error state additions need judgment (what should happen on error? depends on the app).

## Deployment

**What can go wrong**: app doesn't actually run after deploy.

**Patterns to check**:

- Build succeeds (`npm run build` / `yarn build` / `python -m build` / `cargo build --release`)
- Smoke test passes (entrypoint runs without immediately crashing — `node app.js & sleep 5 && kill $!` style)
- Dockerfile builds (if applicable)
- Health check endpoint responds (if applicable)
- Environment variables documented (`.env.example` matches what the code reads)

**Auto-fix**: usually not. Deploy failures often need user attention.

## Templates extend these

A `doc-verification` template might add:
- Rules cover all chapters of the source regulation
- Each rule has a test case
- Confidence calibration data is non-empty

A `slides-from-textbook` template might add:
- Slide deck opens in a headless browser without errors
- Every slide has visible content (not empty)
- Media is inlined (no external CDN refs that could break)

These are domain-specific; the four categories above are universal.

## What does NOT belong here

- **Performance** (this app loads slowly): requires profiling, not pattern matching. Different skill.
- **Architecture concerns** (the structure could be cleaner): subjective, not a guardrail. Cross-validation territory if anywhere.
- **Feature completeness** (this should have a chatbot too): out of scope for guardrails; that's a PLAN.md change.

## Source

Categories synthesized from spec §8.14 (skills2app's existing patterns) + skills2app's own code-quality reviews + create-any-portfolio's 15+ deterministic guardrails documented in its `docs/code-guardrails.md` on the dev machine.
