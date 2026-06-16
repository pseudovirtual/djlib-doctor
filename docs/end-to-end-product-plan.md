# End-To-End Product Plan

This is the working checklist for turning `djlib-doctor` into a small, robust open-source DJ library toolkit.

## Product Bar

The project should be:

- easy to install and smoke-test
- useful as both a CLI and Python library
- safe by default but complete when the user approves staged writes
- modular enough to add Traktor, Engine, VirtualDJ, or other adapters later
- agent-discoverable through docs, schemas, skills, and predictable command names
- pleasant for human contributors to understand

## Architecture Checklist

- [x] Core library model for tracks, playlists, cues, and locations
- [x] Rekordbox XML reader
- [x] Serato SQLite/crate reader/writer surface
- [x] Staged write safety helpers
- [x] Rekordbox to Serato dry-run manifest
- [x] Rekordbox to Serato staged SQLite/crate install
- [x] Rekordbox to Serato staged Serato audio-tag install
- [x] Generic staged file operations
- [x] Generic staged SQLite operations
- [x] Workflow API for Rekordbox to Serato
- [x] Serato to Rekordbox dry-run manifest
- [x] Serato to Rekordbox port manifest and XML representation
- [x] High-level Serato-to-Rekordbox staged `master.db` import wrapper
- [x] Fixture-backed Serato Markers2 cue reader into Serato-to-Rekordbox manifests
- [ ] Higher-level interactive review/prompt flow for migrations
- [x] User config file for local paths and defaults
- [ ] Public API docs with short examples
- [x] Fixture-backed Serato-to-Rekordbox cue preservation tests for supported schemas
- [ ] CLI naming cleanup and alias pass

## Safety Checklist

Every write-capable workflow must have:

- [x] explicit stage command
- [x] install/apply command separate from planning
- [x] exact confirmation token
- [x] backup path
- [x] hash verification
- [x] synthetic tests
- [ ] app-closed checks for every app-specific live install
- [ ] documented rollback steps

## User Experience Checklist

- [x] `djlib-doctor self-test`
- [x] manual step-by-step commands
- [x] workflow command: `migrate rb-to-serato`
- [x] workflow command: `migrate serato-to-rb`
- [x] `config init` and `config show`
- [ ] short "try one playlist first" docs
- [ ] concise README path for DJs
- [ ] longer architecture docs for contributors

## Agent Experience Checklist

- [x] `AGENTS.md`
- [x] `AGENTS.md`
- [x] `llms.txt`
- [x] report schemas via `djlib-doctor schema`
- [ ] agent recipe: inspect, plan one playlist, stage, ask user, install
- [ ] agent recipe: convert formats without losing cues
- [ ] skill update after every command rename

## Near-Term Implementation Order

1. Add broader Rekordbox DB schema adapters for playlists and cue tables found in real libraries.
2. Add a small config system for path/default discovery.
3. Refactor repeated staging hash/token helpers into shared utilities.
4. Add migration recipe docs for human and agent workflows.
5. Add interactive migration review command.
6. Add more cue/tag round-trip fixtures when optional audio dependencies are available.
