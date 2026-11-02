## Development workflow

Development is spec-driven and incremental.

- Each meaningful gameplay increment should have a small Markdown spec in
  `/specs`.
- Specs are numbered sequentially (`001-...`, `002-...`, etc.).
- A new spec should normally be committed before or together with its
  implementation so that the repository records both intent and code.
- Read the relevant spec completely before implementing it.
- Also inspect the existing project before making changes.
- Implement only the scope described by the current spec.
- Specs describe the change to make, not the complete desired state of the
  project. Existing working behavior outside the spec should be preserved.
- Prefer simple solutions over speculative abstractions.
- Do not automatically implement future work mentioned by a spec.
- `TODO.md` contains intentionally deferred work and is not an implementation
  queue unless explicitly requested.
- After implementing a task, update `TODO.md` to move completed work to the bottom of the done list and add
  any newly identified deferred work.
- When implementation reveals that a spec is ambiguous or conflicts with the
  existing project, surface the issue rather than silently expanding scope.
- After implementation, summarize the changes and identify any manual
  configuration required.
- Historical specs describe the intent of an increment at the time it was
  implemented. Do not rewrite old specs merely because the implementation
  evolves later.
