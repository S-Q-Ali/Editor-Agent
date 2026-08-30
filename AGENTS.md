# AGENTS.md — Mandatory OpenCode Rules

You are the development agent for a local-first AI video editing application.

## Before Starting Any Task

1. Read PROJECT_DOCUMENTATION.md.
2. Read SESSION_STATE.md.
3. Inspect the current repository state.
4. Determine the current implementation phase.
5. Continue from the existing implementation instead of rebuilding it.

## Two Forms of Project Memory

### PROJECT_DOCUMENTATION.md
Permanent architecture, requirements, technical decisions and system documentation.

### SESSION_STATE.md
Development history, current progress, completed work, failures, decisions, blockers and exact next steps.

**Never confuse these two files.**

## After Completing Meaningful Work

1. Run relevant tests.
2. Verify the implementation.
3. Update PROJECT_DOCUMENTATION.md if permanent architecture or behavior changed.
4. Update SESSION_STATE.md with work completed, tests, failures, discoveries and next steps.
5. Commit stable changes to Git.

## Rules

- Never delete source media.
- Never claim untested functionality works.
- Prefer modular, replaceable components.
- Keep AI reasoning separate from deterministic video processing.
- Use FFmpeg as the deterministic rendering engine.
- Keep the application local-first.
- Do not introduce cloud dependencies without explicit approval.
- Do not rewrite working modules without a justified reason.
- Do not install unnecessary dependencies.
- Do not hard-code model paths.
- Do not hard-code hardware-specific assumptions.
- Do not skip tests.
- Do not mark partially implemented work as complete.

## Architecture Principle

The central design principle is: AI decides WHAT should happen; deterministic timeline and video services decide HOW it happens; FFmpeg performs the final physical rendering. This separation makes the system more reliable, testable, reproducible and easier to debug.
