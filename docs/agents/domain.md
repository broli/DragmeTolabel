# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

This repo uses a **single-context** layout: one `CONTEXT.md` at the repo root and documentation in `docs/`.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — the project's glossary and domain language.
- **`docs/architecture.md`** — system architecture and rendering data flow.

## File structure

```
/
├── CONTEXT.md          ← glossary and domain terminology
├── docs/               ← architecture and documentation
│   ├── architecture.md ← system architecture & pipeline data flow
│   └── agents/         ← agent exploration guidance
├── backend/            ← FastAPI & OpenCV engine
│   └── app/
│       ├── api/        ← REST route handlers
│       ├── core/       ← geometry schemas, presets, labelme bridge
│       └── cv/         ← homography, materials, lighting, renderer
├── frontend/           ← Web visualizer (HTML5 canvas, loupe, slider)
└── tests/              ← Pytest suite
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap.
