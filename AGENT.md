# AGENT.md

## 1. Purpose of this file

Use this file as the operating manual for autonomous changes in this repository.

Priority order when making decisions:

1. Explicit user request
2. Current repository behavior proven by code, tests, and CI
3. Safety and correctness
4. Minimal, reversible changes

When README/docs and tests disagree, prefer the tests and CI workflows. Call out the mismatch in your handoff.

## 2. Repository overview

- `pathy-svg` is a single-package Python library for turning arbitrary SVGs into data-driven visualizations.
- The main user-facing entrypoint is `SVGDocument` in `src/pathy_svg/document.py`.
- The package supports:
  - heatmaps and categorical recoloring
  - legends, annotations, tooltips, and animation
  - diff/compare views across datasets
  - SVG inspection/validation
  - raster export to PNG/PDF/JPEG through optional dependencies
  - a Click CLI exposed as `pathy-svg`
- Tech stack actually present:
  - Python 3.10-3.13
  - `lxml`, `matplotlib`, `numpy`, `click`
  - optional `cairosvg`, `Pillow`, `IPython`
  - `pytest` for tests
  - Hatchling for builds
  - Ruff config is present in `pyproject.toml`, but linting/formatting is not part of CI
  - `pdoc`-generated HTML docs are committed under `docs/`

Architectural boundaries:

- `SVGDocument` is an immutable wrapper. Public "mutation" methods are expected to return a new document.
- Low-level helper modules usually mutate an `lxml` tree in place.
- Mixins in `src/pathy_svg/_mixins/` are the bridge: they clone first, then call the helper logic.
- `src/pathy_svg/__init__.py` is the public export surface and version source.

Not present:

- No monorepo/workspace tooling
- No database, migrations, or seeding
- No Docker/devcontainer setup
- No environment-variable-driven runtime configuration

## 3. Working rules for agents

Always do this before editing:

- Read the nearby implementation file and its corresponding test file(s).
- Check whether the change affects the public API in `src/pathy_svg/__init__.py`.
- Check whether the change affects CLI behavior in `src/pathy_svg/cli.py`.
- If packaging behavior may change, inspect `tests/test_packaging.py` and `pyproject.toml`.

Always preserve these behaviors unless the user explicitly asks otherwise:

- Public `SVGDocument` methods that change output should clone first and return a new object.
- Helper modules may mutate the passed tree, but should not silently mutate the caller's original document.
- Recoloring/heatmap logic should keep SVG presentation attributes and inline CSS in sync.
- Optional dependencies should fail lazily with helpful install instructions via `src/pathy_svg/_compat.py`.
- CLI commands should use `click.echo` and `click.BadParameter`/exit codes for user-facing failures.

Do not do these without explicit instruction:

- Rename or remove public exports from `src/pathy_svg/__init__.py`
- Change CLI flags, command names, or output semantics
- Add new runtime dependencies
- Change packaging contents/excludes in `pyproject.toml`
- Modify release/publish workflows under `.github/workflows/`
- Edit generated docs in `docs/` as a source-of-truth

Diff policy:

- Prefer minimal diffs over refactors.
- Refactor only when required to make the change correct or maintainable.
- Follow existing patterns instead of introducing a new abstraction style.

Files and areas that should usually not be edited directly:

- `docs/` HTML files: generated output, not the source template
- `dist/`, `.venv/`, `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`: local artifacts
- `uv.lock`: present locally but gitignored; do not treat it as committed repository state

Special caution:

- `src/pathy_svg/__init__.py` holds `__version__`, which Hatch uses for builds.
- Version changes affect artifact names and `tests/test_packaging.py`.

## 4. Repository map

Core package:

- `src/pathy_svg/document.py`
  - composed `SVGDocument` class; primary user entrypoint
- `src/pathy_svg/_base.py`
  - loading, querying, cloning, id indexing, geometry access
- `src/pathy_svg/_mixins/`
  - public document methods layered by concern
  - `coloring.py`, `legend.py`, `diff.py`, `annotations.py`, `animation.py`, `export.py`, `serialization.py`
- `src/pathy_svg/coloring.py`
  - core recolor/heatmap/category logic; mutates trees in place
- `src/pathy_svg/legend.py`, `annotations.py`, `diff.py`, `export.py`, `inspect.py`
  - helper logic for each feature area
- `src/pathy_svg/themes.py`, `color.py`, `data.py`, `svg_tools.py`, `transform.py`, `utils.py`
  - supporting utilities and value transformations
- `src/pathy_svg/cli.py`
  - Click CLI entrypoint for `pathy-svg`

Tests:

- `tests/`
  - module-oriented pytest suite
  - most tests assert on SVG strings, XML element attributes, and package contents
- `tests/fixtures/`
  - small canonical SVG fixtures: `simple.svg`, `styled.svg`, `grouped.svg`

Examples:

- `examples/`
  - shipped example assets used in docs and packaging tests

Docs:

- `README.md`
  - install, quick-start, CLI examples, API summary
- `docs/`
  - generated `pdoc` HTML output
- `docs_templates/`
  - Jinja override for the generated docs theme/title

CI/release:

- `.github/workflows/ci.yml`
  - build + full pytest matrix on Python 3.10-3.13
- `.github/workflows/publish.yml`
  - release publishing to PyPI

Usually ignore during code scanning unless the task requires them:

- `dist/`
- local caches and virtualenvs
- `docs/` generated HTML
- local notebook `examples.ipynb` if present

## 5. Commands agents should use

Install dependencies:

- CI-proven install path:
  - `python -m pip install --upgrade pip`
  - `pip install -e ".[export,full]"`
  - `pip install pytest build hatchling`
  - Use this when you need the same dependency set CI uses.
- Inferred local shortcut:
  - `uv sync --dev`
  - Use only if `uv` is available locally. `uv.lock` is gitignored, so CI does not rely on it.

Run the package / smoke-test CLI:

- `pathy-svg inspect examples/map.svg`
  - Fast smoke test for CLI wiring and package install.
- `pathy-svg heatmap examples/map.svg examples/data.csv --id-col organ --value-col expression --palette YlOrRd --legend -o out.svg`
  - Useful manual end-to-end check for core functionality.

Build distributions:

- `python -m build --sdist --wheel --no-isolation`
  - Preferred packaging validation command.
  - Run this if you changed `pyproject.toml`, package layout, versioning, or shipped files.

Lint:

- Inferred: `ruff check .`
  - Use if Ruff is installed locally.
  - Repo has Ruff config in `pyproject.toml`, but CI does not run it.

Format:

- Inferred: `ruff format .`
  - Use if Ruff is installed locally.
  - No separate formatter config is committed.

Typecheck:

- None configured.
  - The package is typed (`py.typed` is shipped), but no mypy/pyright command is configured in the repo.

Run all tests:

- `pytest`
  - This is the main CI validation command.
  - Run it from an environment where `pathy_svg` is installed editable, such as after the install steps above or via the project `.venv`.

Run a single file or narrow subset:

- `pytest tests/test_cli.py`
- `pytest tests/test_cli.py -k heatmap`
- `pytest tests/test_packaging.py`
  - Prefer narrow pytest runs first, then broaden if shared code changed.

Integration / end-to-end:

- No separate integration framework is configured.
- CLI coverage lives inside the normal pytest suite.

Docs generation / preview:

- No committed docs-generation command is documented in the repo.
- Inferred from `docs/pathy_svg.html`: docs were generated with `pdoc 16.0.0`.
- Only regenerate docs if the task explicitly includes docs publishing or committed HTML updates.

Database / migrations / seeding:

- Not applicable.

Codegen:

- No general-purpose codegen is configured.
- The only generated content visible in-repo is the `pdoc` HTML in `docs/`.

Clean / reset:

- No repo-specific clean command exists.
- Prefer targeted validation over deleting local artifacts.
- Do not remove local files unless the user explicitly asks for cleanup.

## 6. Coding conventions inferred from the repo

Strong conventions visible in code:

- Absolute imports are preferred inside the package: `from pathy_svg...`
- Most modules use `from __future__ import annotations`
- Module/class/function docstrings are common and should be maintained
- Mixins commonly declare `__slots__ = ()`; the base document class uses explicit `__slots__`
- Public mutation-style APIs return new `SVGDocument` instances
- Helper functions often mutate the provided XML tree directly

Error handling:

- Library code raises custom exceptions from the `PathySVGError` hierarchy where appropriate
- Simple argument validation may raise `ValueError`
- CLI code uses Click-native error handling and exit codes
- Logging is minimal; library code mostly raises, while CLI code may warn for recoverable issues

Typing expectations:

- Use standard Python type hints; union syntax like `str | Path` is already in use
- Preserve the package's typed surface; changes to exported types should be treated as public API changes

State and data patterns:

- Data is passed mostly as plain dictionaries keyed by SVG element IDs
- Small structured values use dataclasses/value objects rather than heavy frameworks
- Optional pandas support is tested via `pytest.importorskip("pandas")`

SVG/document conventions:

- Keep presentation attributes and inline `style` synchronized when changing fill/stroke
- Preserve explicit unfilled elements (`fill="none"` or `style="fill:none"`) when coloring missing data
- Avoid renaming hard-coded overlay IDs unless explicitly intended:
  - `pathy-legend`
  - `pathy-annotations`
  - `pathy-guide`
- Animation CSS names with `pathy-...` prefixes are asserted in tests

Testing conventions:

- Tests are grouped into `Test...` classes under `tests/test_*.py`
- Assertions are usually structural/string-based, not snapshot-based
- Optional dependency coverage uses `pytest.importorskip(...)` or `@pytest.mark.skipif(...)`
- If you add a feature, add focused tests in the matching module-oriented test file

Where conventions are weaker:

- Linting/formatting is not enforced in CI
- No static typechecker is configured
- There is no CONTRIBUTING guide defining broader style rules

When conventions are weak, match the surrounding file instead of introducing a new style.

## 7. Validation checklist before finishing

- Change scope is minimal and limited to the requested behavior
- No unrelated files were modified
- Relevant tests pass
- `pytest` passes if shared/core behavior changed
- `pytest tests/test_cli.py` passes if CLI behavior changed
- `pytest tests/test_packaging.py` passes if packaging/version/shipped-file behavior changed
- `python -m build --sdist --wheel --no-isolation` passes if packaging changed
- Ruff checks/formatting were run if available and appropriate
- README or docs were updated if user-visible behavior changed
- No generated/local artifact files were accidentally edited or committed

## 8. Project-specific pitfalls

- `SVGDocumentBase` caches an element-id index. Public mutation methods must clone first; direct tree mutation without cache awareness is risky.
- Bare `pytest` from a global Python without an editable install will fail collection because the repo does not configure `pythonpath=src`.
- Packaging tests may reuse existing `dist/` artifacts if the version matches. Fresh builds are safer when validating packaging changes.
- Source distributions intentionally include `tests/` and `examples/`, but intentionally exclude `.github/`, `docs/`, and `docs_templates/`.
- Export tests depend on `cairosvg` and a working Cairo stack. They may skip or fail locally even when core logic is fine.
- The repo contains Ruff config, but CI does not enforce linting; do not assume a clean `pytest` run means style tooling ran.
- `uv.lock` and `examples.ipynb` are local/ignored artifacts, not committed repository inputs.
- Docs under `docs/` are generated by `pdoc`; template changes belong in `docs_templates/`.
- CLI CSV parsing skips non-numeric rows with a warning rather than failing the whole command. Preserve that behavior unless explicitly changing CLI semantics.
- Recolor/heatmap behavior is tested against both `style` and `fill` attributes. Changing only one will regress tests and renderer compatibility.

## 9. Safe change strategy

Default strategy:

1. Inspect the target module and the matching tests first.
2. Check whether the change touches a public API, CLI surface, or packaging boundary.
3. Follow the existing split:
   - helper module for tree mutation logic
   - mixin wrapper for immutable document behavior
4. Make the smallest correct change.
5. Run the narrowest useful pytest target first.
6. Broaden to full `pytest` and packaging build checks if shared code or shipped files changed.
7. Note any assumptions, skipped checks, or optional-dependency gaps in the handoff.

## 10. Handoff expectations

In the final handoff, report:

- What changed
- Why the change was needed
- Which validation commands were run
- What was not verified
- Any public API, CLI, packaging, or docs impact
- Any follow-up risk, especially around optional dependencies or generated docs
