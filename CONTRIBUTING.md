# Contributing

`djlib-doctor` is private and early right now, but the contribution model should be open-source friendly from the start.

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
- Keep write-capable behavior out of early milestones.
- Add tests for every user-visible behavior change.

## Running Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Documentation

Update docs when behavior changes. The README is for DJs first, developers second.
