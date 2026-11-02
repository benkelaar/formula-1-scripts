# Formula 1 All-Time Championship Animation

A Python application that retrieves historical Formula 1 championship data and
turns cumulative all-time driver rankings into a polished animated bar chart
race.

## Development tooling

- Use `uv` to manage the Python version, virtual environment, and dependencies.
- Add and remove Python dependencies through `uv`; do not manually maintain a
  parallel `requirements.txt` workflow.

## Development workflow

Development is spec-driven and incremental.
- Each meaningful project increment should have a small Markdown spec in
  `/specs`.
- Specs are numbered sequentially (`001-...`, `002-...`, etc.).
- A new spec should normally be committed before or together with its
  implementation so that the repository records both intent and code.
- Before implementing anything, always present the relevant spec to the user
  and receive their explicit validation of it. Do not begin implementation
  until the user has approved the spec.
- If the user identifies ambiguity, missing acceptance criteria, or a conflict,
  update the spec and ask them to validate the revised version before coding.
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

## Simplicity and scope

- Choose the smallest change or investigation that directly answers the current
  request.
- Do not turn a one-off check, audit, or report into a reusable subsystem unless
  the user asks for that subsystem or the current implementation requires it.
- Before adding schemas, commands, abstractions, generated artifacts, or atomic
  publication machinery, identify the current consumer that needs them. Defer
  them when the need is only hypothetical or belongs to a later increment.
- A spec should be proportional to the change. Small, low-risk work may need
  only a short spec or an update to an existing one; analysis-only work does not
  require a new implementation spec.
- Prefer inspecting the actual data and reporting concrete findings before
  designing infrastructure intended to handle possible findings.
- When a simpler approach satisfies the acceptance criteria, use it even if a
  more elaborate approach could be more reusable later.
