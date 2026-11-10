# Commit policy

Commit history is a navigation index for agents and maintainers. A subject should
identify the affected subsystem and the concrete change without requiring the
reader to open the diff.

## Subjects

Use `<type>(<scope>): <imperative description>`. Aim for 50–72 characters;
clarity takes priority over a rigid limit. Use `feat`, `fix`, `refactor`, `test`,
`docs`, `build`, or `chore` according to the primary intent. Name the behavior or
artifact; avoid subjects such as “update files,” “misc fixes,” or “finish phase 2.”

Use these stable scopes rather than inventing synonyms:

| Scope | Location or responsibility |
| --- | --- |
| `repo` | Repository guidance and shared tooling |
| `program` | Cross-pilot plans and portfolio strategy in `docs/` |
| `fluidstack` | Documentation or inseparable changes across this pilot |
| `fluidstack-fixtures` | Synthetic IFC/procurement data and its generator |
| `fluidstack-engine` | IFC extraction, revision comparison, BOM/PO impact |
| `fluidstack-api` | HTTP contracts, persistence, and audit CLI |
| `fluidstack-web` | Viewer, browser workflow, and frontend build |
| `fluidstack-demo` | Local launch orchestration and demonstration capture |

The pilot root is `pilots/fluidstack-change-auditor/`. For another pilot, establish
a short, stable prefix and extend this table. Choose one scope for the primary
responsibility; do not concatenate scope names.

Examples:

```text
feat(fluidstack-engine): trace IFC revisions to BOM and PO changes
fix(fluidstack-web): pin Vite for CPUs without BMI2
docs(fluidstack): record the remaining Bonsai authoring gate
```

## Bodies

Omit the body when the subject and diff explain the change. Otherwise add only
the rationale, a non-obvious constraint, or a compatibility consequence. Keep
paragraphs short. Use real paths, symbols, and issue identifiers when useful;
avoid narrating tool calls or repeating the file list.

For behavior changes, include a concise `Validation:` line naming checks actually
run and their outcome, or stating what remains unverified. Documentation-only
changes need no test boilerplate. Never imply a check passed without running it.

## Boundaries and dependency order

- Give each commit one coherent purpose that a reviewer can inspect or revert.
  Include tests with their implementation and lockfiles with manifest changes.
- Commit prerequisites before consumers: runtime and fixtures → engine → API →
  viewer → demo integration → evidence. Independent documentation can stand alone.
- Each intermediate revision must support the capabilities it introduces without
  relying on files that appear only in a later commit. A partial pilot need not
  provide the final demo yet.
- Keep generated environments, dependencies, caches, build outputs, local
  databases, credentials, and crash dumps out of Git. Deliberately versioned
  fixtures and portfolio evidence belong with their provenance or documentation.
- Split unrelated fixes. Keep a tightly coupled change together when splitting
  would break an interface. Do not create empty scaffolding commits or one commit
  per file merely to increase granularity.
- Review the exact staged diff, run `git diff --cached --check`, and validate the
  affected behavior before committing. State any material validation limitation.
- Do not rewrite published history or push unless the user authorizes it.

## Navigating history

```bash
# Find subsystem changes, then inspect one commit.
git log --oneline --grep='(fluidstack-engine):' --fixed-strings
git show --stat <commit>
git show <commit> -- pilots/fluidstack-change-auditor/engine/

# Follow a path or inspect the dependency order of the initial implementation.
git log --oneline -- pilots/fluidstack-change-auditor/api/
git log --reverse --oneline
```

Prefer paths for exact ownership and scopes for related changes spanning paths.
Commit messages describe the change at that revision; current usage belongs in
READMEs and current limitations belong in validation records.
