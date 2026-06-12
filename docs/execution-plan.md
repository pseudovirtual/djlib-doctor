# Execution Plan

This project should stay small, safe, and easy for DJs and agents to call.

## Current Milestone

Stabilize the open-source core:

- keep modules focused and under 200 lines where practical
- keep command output predictable for agents
- keep tests synthetic and easy to run
- keep staged writes token-gated and hash-verified
- keep README/docs concise enough for humans

## Guardrail Commands

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src PYTHONPYCACHEPREFIX=work/pycache python3 -m compileall -q src tests
PYTHONPATH=src python3 -m djlib_doctor.cli self-test
```

## Build Order

1. Verification and snapshots.
2. Read-only plans and review logs.
3. Dry-run port manifests.
4. Staged installs with backups, hashes, and exact tokens.
5. Packaging and public release.

## Done

- Rekordbox XML parse/verify/snapshot/compare.
- Missing-file, duplicate, cue, bad-path, and audio-compatibility plans.
- Interactive review and dry-run apply manifests.
- Rekordbox-to-Serato and Serato-to-Rekordbox dry-run planning.
- Serato library, audio-tag, file-op, and SQLite staged install flows.
- Config, schema, skill, and plugin-template scaffolding.

## Next

- CLI split and naming polish.
- More shared internals for reports and manifests.
- More Serato cue/tag round-trip fixtures.
- Public release checklist, license, changelog, and CI.
