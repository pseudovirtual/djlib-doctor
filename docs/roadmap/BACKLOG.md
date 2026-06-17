# Roadmap Backlog

Scope: Rekordbox and Serato only. Do not add other DJ apps or a neutral universal model.

## Operating Rules

- Use TDD for user-visible behavior.
- Use synthetic fixtures and existing golden vectors.
- Keep write workflows behind stage/install tokens, hashes, backups, sidecar checks, and app-closed checks.
- Prefer small modules, explicit CLI verbs, and DRY platform-neutral helpers.
- Keep every interactive command scriptable with flags or tokens.

## Phase A - Primary-Library Foundation

- [x] S0: Create `docs/roadmap/BACKLOG.md` and `docs/roadmap/STATE.md` from the active backlog.
- [x] A1: Add `primary` (`rekordbox` or `serato`) plus target paths to config and `config init` / `config show`. Default primary is `rekordbox`. Test load, validation, and round trip.
- [x] A2: Add `djlib-doctor detect` to read-only probe default Rekordbox and Serato locations, including Rekordbox `master.db` or exported XML, Serato `_Serato_`, external-drive libraries, `database V2`, `Subcrates`, and `root.sqlite`. Print text and `--json`.
- [x] A3: Use config-driven defaults: explicit args first, then config, then detection, with clear errors if still unknown. Make `verify` work with no args against the configured or detected primary.

## Phase B - One-Command Porting

- [x] B1: Add a projection/sync planner that takes the configured primary and target, then produces the existing dry-run port manifest and certification. Reuse current port and certify code. Direction is chosen by `primary`.
- [x] B2: Add `djlib-doctor sync` for the full safe interactive pipeline: preview, typed confirmation, stage, and install. Non-interactive mode uses `--yes` or `--confirm-token`.
- [x] B3: Keep destructive paths dry-run by default: show preview/diff and require explicit confirmation or `--apply`. Backups are automatic.

## Phase C - Friendly Entry Points

- [x] C0: Enrich `sync` preview output so it prints certification summary counts for matched/unmatched tracks, cues, loops, playlists, and unsupported rows before confirmation.
- [x] C1: Add `djlib-doctor doctor`: detect libraries, verify each found library, and print a prioritized punch list with exact next commands.
- [x] C2: Make bare `djlib-doctor` open a small interactive menu: doctor, sync, fix, config, quit. Each option calls the corresponding verb with detected defaults.

## Phase D - Review Polish

- [x] D1: Improve interactive review: Enter accepts recommended choice, `A` accepts recommended for remaining high-confidence rows, `u` undoes the last decision, and a live progress header is shown. Keep stdlib-only.
