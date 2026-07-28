# AGENTS.md

## Project

This repository contains a local, mobile-first VLC remote control for macOS.

The React frontend runs in a phone browser or as a PWA. It communicates with a
FastAPI backend. The backend communicates with VLC's localhost-only HTTP
interface.

Read `SPEC.md` before making architectural or behavioural changes.

## Primary constraints

- Never expose the VLC password to the frontend.
- Never expose arbitrary VLC commands through the API.
- Never execute browser-provided shell commands or AppleScript.
- Never commit `.env`, access tokens, passwords or generated configuration.
- State-changing operations must use POST.
- Do not use wildcard CORS in production.
- Keep the frontend and production API on the same origin.
- Do not claim that a VLC command was tested against real VLC unless it was.
- Keep all VLC-specific parsing and command mapping behind the VLC adapter.
- Automated tests must not require a running VLC instance.

## Repository structure

- `backend/app`: FastAPI application.
- `backend/tests`: backend tests and VLC fixtures.
- `frontend/src`: React and TypeScript frontend.
- `frontend/tests`: frontend tests.
- `scripts`: bootstrap, diagnostics and run scripts.
- `docs`: architecture, setup, security and testing documentation.

## Commands

Keep these commands working:

- `make bootstrap`
- `make dev`
- `make build`
- `make lint`
- `make typecheck`
- `make test`
- `make run`

If command names change, update this file and README.md in the same change.

## Backend conventions

- Use typed Python.
- Use Pydantic models for API inputs and outputs.
- Use dependency injection for the VLC client.
- Use application-specific exceptions.
- Use one reusable HTTPX async client.
- Validate all external input.
- Avoid leaking internal exception text to clients.
- Add tests for bug fixes and new behaviour.
- Format and lint with Ruff.
- Type-check with mypy.

## Frontend conventions

- Use TypeScript in strict mode.
- Use semantic, accessible HTML.
- Optimise for small phone screens first.
- Keep API access in the API client module.
- Keep token handling in the auth module.
- Do not add third-party runtime scripts.
- Do not send a seek command for every slider movement.
- Clean up polling timers and aborted requests.
- Add tests for user-visible state changes.

## Security review

For each feature, consider:

- Authentication bypass.
- Secret leakage.
- Arbitrary command injection.
- Unsafe URL handling.
- Missing input validation.
- Excessive network exposure.
- Sensitive logging.
- Cross-origin behaviour.
- PWA cache behaviour.

## Verification before completion

Run:

1. Formatting.
2. Linting.
3. Type checking.
4. Backend tests.
5. Frontend tests.
6. Frontend production build.
7. End-to-end tests where configured.

Inspect `git diff` and report:

- Files changed.
- Commands run.
- Test results.
- Manual verification performed.
- Manual verification still required.
- Remaining risks or limitations.

Do not mark work complete when a required test is failing.
