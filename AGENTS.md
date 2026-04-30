# Compas Agent Guide

This file gives AI coding agents the minimum project context to be productive quickly.

## Primary References

- Full functional specification: [CLAUDE.md](CLAUDE.md)
- User workflow and data format overview: [README.md](README.md)

Use those documents as source of truth. Do not duplicate their full content in code changes.

## Setup and Validation Commands

- Install dependencies: `poetry install`
- Run tests: `poetry run pytest`
- Lint: `poetry run ruff check src tests`
- Format: `poetry run ruff format src tests`

## Main CLI Commands

- Import xlsx to SQLite: `poetry run compas import`
- Generate dashboard HTML: `poetry run compas dashboard`
- Run full pipeline: `poetry run compas build`

Common options:

- `--data DIR`
- `--db FILE`
- `--out FILE`
- `--alpha FLOAT`
- `--open`

## Architecture Map

- `src/compas/cli.py`: CLI parsing, logging setup, command dispatch
- `src/compas/importer.py`: xlsx parsing and SQLite import
- `src/compas/ema.py`: EMA, trend, rank logic
- `src/compas/dashboard.py`: DB read + HTML generation through Jinja2
- `src/compas/templates/dashboard.html`: static dashboard template

## Project-Specific Rules

- Import is destructive: the SQLite schema is dropped and rebuilt on each import.
- Parsing errors should log warnings and continue when possible.
- Structural errors should fail fast with explicit exceptions.
- Use `logging`, not `print`.
- Keep type hints on public functions.
- Keep docstrings/comments in French when adding or updating them.

## High-Risk Pitfalls

- Sheet filtering is strict:
  - `Config` is exact-match and case-sensitive.
  - `Modele` / `Modele with accent` are ignored via accent-insensitive matching.
  - `tmp-` prefix is ignored case-insensitively.
- Student matching between Config and session sheets is by exact name.
- Presence parsing supports combined tokens (`TYPE:value:motif` with comma separators).
- EMA ignores null observations and uses only observed scores.

## Testing Guidance

- Prefer targeted test runs while iterating, then run full test suite.
- If you change importer behavior, run `tests/test_importer.py`.
- If you change EMA/rank behavior, run `tests/test_ema.py`.
- If you change dashboard rendering/data prep, run `tests/test_dashboard.py`.

## Session Tracking

- Update [PROGRESS.md](PROGRESS.md) at the end of each session.
- Add one new dated entry under "Journal de session" with objective, delivered work,
  checks run, residual risks, and next actions.
