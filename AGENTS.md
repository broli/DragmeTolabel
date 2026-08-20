# CLAUDE.md

## Repository & Development Guidelines

### Git Branching Strategy & Workflow

1. **Branch Hierarchy**:
   - `main`: Production release branch. Must always be stable. Direct pushes and force-pushes are strictly forbidden.
   - `Dev`: Primary integration branch. All active development, feature branches, and fixes branch from and merge into `Dev`.
   - `<author>/<type>-<short-description>`: Working branches for all changes.
     - `type` values: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `ci`.
     - Examples: `carlos/feat-alcove-bath-preset`, `carlos/fix-homography-warp`, `carlos/docs-architecture`.

2. **Commit Message Conventions**:
   - All commits must follow [Conventional Commits](https://www.conventionalcommits.org/):
     - `feat(scope): ...` for new features
     - `fix(scope): ...` for bug fixes
     - `refactor(scope): ...` for code refactoring without behavior changes
     - `docs(scope): ...` for documentation changes
     - `test(scope): ...` for test suite modifications
     - `chore(scope): ...` for dependency, build, or tooling updates
   - Scope examples: `cv`, `preset`, `lighting`, `api`, `frontend`, `bridge`, `config`.

3. **Pull Request & Integration Rules**:
   - All PRs must target the `Dev` branch.
   - PRs must pass automated linting (`ruff check`) and the full pytest suite (`pytest -v`) before merge.
   - Rebase or squash onto `Dev` to keep linear and clean commit history.

---

## Changelog SOP

User-facing changes go in `CHANGELOG.md` under `## [Unreleased]` ([Keep a Changelog](https://keepachangelog.com/) format), filed in the right `### Added/Changed/Removed/Fixed` subsection with the PR number linked. Prefix `**Breaking:**` for changes that bump the major version. At release, the `[Unreleased]` section is promoted to the new version.

---

## Architecture & Project Structure

- **`backend/app/cv/`**: Computer Vision engine.
  - `homography.py`: OpenCV perspective homography computation (`cv2.getPerspectiveTransform`, `cv2.warpPerspective`).
  - `materials.py`: Material catalog, procedural texture synthesis, and pattern loaders.
  - `lighting.py`: Luminance extraction, shadow preservation, and realistic highlight blending.
  - `renderer.py`: End-to-end rendering pipeline composing warped materials onto room photos.
- **`backend/app/core/`**: Domain models and core business logic.
  - `schemas.py`: Pydantic data models for polygons, planes, presets, and API payloads.
  - `presets.py`: 2.5D surface presets (`floor`, `ceiling`, `corner_bath`, `alcove_bath`, `cali_bath`).
  - `labelme_bridge.py`: Headless exporter converting DragMeToLabel geometry to standard Labelme 5.x JSON.
- **`backend/app/api/`**: FastAPI REST API endpoints.
  - `routes_preview.py`: `/api/v1/presets`, `/api/v1/materials`, `/api/v1/preview`, `/api/v1/export-labelme`.
- **`frontend/`**: Interactive tablet/desktop web application.
  - Vanilla HTML5 / CSS3 / ES6 modules.
  - Features: Interactive canvas with control point dragging, touch loupe magnifier, comparison slider, material swatches.
- **`tests/`**: Pytest test suite (`tests/test_backend.py`).
- **`docs/`**: Architecture and system documentation (`docs/architecture.md`, `docs/agents/domain.md`).

---

## Developer Commands & Workflows

```bash
# Start local development server (port 8000)
make dev
# or
uvicorn backend.app.main:app --reload --port 8000

# Run automated tests
make test
# or
pytest -v

# Run linter and formatting checks
make lint
make format
make check
```

---

## Agent Skills & Domain Docs

- **`CONTEXT.md`**: Glossary of domain concepts (Presets, Planes, Control Points, Homography, Materials, Lighting Engine, Labelme Bridge).
- **`docs/architecture.md`**: Detailed system architecture and rendering data flow.
- When generating code or documentation, adhere strictly to the established domain terminology defined in `CONTEXT.md`.
