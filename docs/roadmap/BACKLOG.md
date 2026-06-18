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

## Phase E - Polish And Distribution

- [x] E1: Add Ruff lint/format config, dev dependency, CI checks, and apply formatting.
- [x] E2: Add cross-OS CI matrix for Python 3.9 and 3.13.
- [x] E3: Complete package metadata and ship `py.typed`.
- [ ] E4: Add TestPyPI dry-run publishing and clean-venv smoke install workflow. Repo workflow is added; blocked on maintainer TestPyPI trusted-publisher setup.

## Phase F - Real Rekordbox master.db Read/Write

- [x] F1: Make pyrekordbox a default dependency. Keep graceful runtime fallback when the SQLCipher backend or key/database support is unavailable, with distinct messages for backend missing versus key/unsupported DB. Update README/docs.
- [x] F2: Read a real encrypted `master.db` via pyrekordbox into the native Rekordbox/Serato-specific model: tracks, playlists, and cues. Test against the generated encrypted DB fixture. Fail closed with clear messages on unsupported or locked DBs.
- [x] F3: Write to a real encrypted `master.db` through the existing stage/install engine. Generalize Serato-to-Rekordbox import so one track, one playlist, or whole collection land through the same staged path.

## Phase F Verification

- [x] V-F1: Confirm encrypted DB tests run after package install, fail when installed backends are missing, and skip only in deliberately minimal `PYTHONPATH` environments.
- [x] V-F2: Verify `sqlcipher3-wheels` installs across the CI matrix now that it is a core dependency.

## Phase G - Easy One-Off Ports

- [x] G1: Extend detect -> config -> explicit-flag fallback to `port` verbs so ad-hoc directional ports need minimal flags while ignoring configured primary.
- [x] G2: Confirm both directions and all scopes work end-to-end after F3: track, playlist/crate, and collection.

## Phase H - In-Place Rekordbox Doctoring

- [ ] H1: Apply reviewed cleanup plans back into Rekordbox via staged `master.db` writes.
- [ ] H2: Convert files without losing cues: re-encode with presets, update `master.db` and ANLZ references, carry cues across, and compensate for AAC/M4A encoder delay.
- [ ] H3: Move/rename files and update Rekordbox references in the same staged write.

## Phase I - Real-World Validation

- [ ] I1: Validate `master.db` read/write against one real captured library. Blocked until captured data is available.
- [ ] I2: Validate Serato cue/tag fidelity against real Serato output and extend golden vectors. Blocked until captured data is available.
- [ ] I3: Prove a manually corrected beatgrid survives a port/convert end-to-end.

## Phase J - Release

- [ ] J1: Execute the TestPyPI smoke after maintainer trusted-publisher setup, then flip README install instructions only after smoke passes.
- [ ] J2: Cut a real pre-release tag and confirm the release workflow.

## Phase K - Docs Polish

- [ ] K1: Add short how-to docs for "convert without losing cues" and "port one crate", plus a concise README section on why cue-safe migration is hard.
- [ ] K2: Add public API examples and a `djlib-doctor examples` command.
