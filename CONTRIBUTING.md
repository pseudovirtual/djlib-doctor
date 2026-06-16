# Contributing

`djlib-doctor` is an early open-source project. It should stay small, testable, and safe enough for DJs and agents to understand.

## Good First Contributions

- synthetic Rekordbox XML fixtures
- parser tests
- clearer report wording
- documentation for DJ concepts
- JSON report schema tests
- CLI error handling

## Safety Expectations

- Do not add real music files.
- Do not add real user Rekordbox exports.
- Do not add DB-writing behavior without an accepted design.
- Add tests for every user-visible behavior change.

## Engineering Expectations

- Follow TDD for behavior changes: add or update a focused synthetic-fixture test before implementing the feature.
- Keep modules DRY. Prefer shared models, adapters, and staging helpers over copy-pasted platform logic.
- Keep Python and Markdown files under 200 lines where practical. Split files by responsibility before they become dense.
- Preserve the safety boundary: plan, stage, then install with explicit tokens for write-capable flows.
- Prefer small public APIs that compose into larger workflows.

## Running Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Documentation

Update docs when behavior changes. The README is for DJs first, developers second.
