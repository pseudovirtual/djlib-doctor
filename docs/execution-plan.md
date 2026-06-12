# Execution Plan

This plan covers CLI, human documentation, Codex packaging, Claude Desktop packaging, private GitHub preparation, and eventual public open-source release.

It explicitly excludes building a standalone MCP server for now. Claude Desktop extension packaging is allowed later as a distribution surface, but the product should not revolve around MCP until the CLI and reports are excellent.

## Phase 0: Private Repo Foundation

Goal: prepare `pseudovirtual/djlib-doctor` as a private GitHub repository.

Tasks:

- initialize git if needed
- create private GitHub repo under `@pseudovirtual`
- keep MIT license in `LICENSE`
- add `README.md`
- add `AGENTS.md`
- add `CLAUDE.md`
- add `CONTRIBUTING.md`
- add `CODE_OF_CONDUCT.md`
- add `.gitignore`
- add GitHub Actions test workflow
- add issue templates
- add PR template
- add repository topics after creation

Suggested private repo command, to run only when ready:

```bash
gh repo create pseudovirtual/djlib-doctor --private --source . --remote origin --push
```

Recommended GitHub topics:

- `rekordbox`
- `dj`
- `music-library`
- `hotcues`
- `cue-points`
- `xml`
- `library-cleanup`
- `agent-tools`
- `codex`
- `claude-desktop`

Exit criteria:

- repo exists privately under `@pseudovirtual`
- tests run in CI
- README accurately describes current status
- no private user paths or real music metadata are committed

## Phase 1: Great Human README And Docs

Goal: make a human DJ understand the project in 90 seconds.

Tasks:

- make README answer:
  - what is this?
  - who is it for?
  - what does it do now?
  - what does it refuse to do?
  - how do I run the first command?
  - what does the output mean?
- add `docs/feature-list.md`
- add `docs/human-workflows.md`
- add `docs/safety.md`
- add `docs/reports.md`
- add `docs/rekordbox-xml-concepts.md`
- add `examples/reports/`

Human explanation topics:

- collection tracks vs playlist references
- local files vs streaming placeholders
- missing local paths
- hotcues vs memory cues
- cue loops
- why "more XML tracks than Rekordbox tracks" can be normal

Exit criteria:

- a DJ can read the README and know the first safe command
- a developer can read the docs and know where to contribute
- an agent can read `AGENTS.md` or `CLAUDE.md` and avoid unsafe actions

## Phase 2: CLI Polish

Goal: make the read-only verifier feel real.

Tasks:

- add `--json`
- add `--out` (done)
- add `--pretty`
- add `--schema-version` (done)
- add better path display
- add warnings section
- add failures section
- add suggested next actions (done)
- add stable exit codes:
  - `0`: pass
  - `1`: verification found failures
  - `2`: usage error
  - `3`: unreadable or invalid XML
- handle malformed XML gracefully
- handle missing `<COLLECTION>` gracefully
- validate playlist references against collection IDs
- report duplicate TrackIDs
- report unknown `POSITION_MARK` types

Exit criteria:

- CLI output is useful to a DJ
- JSON output is useful to an agent
- test suite covers happy path, warnings, and failures

## Phase 3: Fixture Corpus And Golden Reports

Goal: prove behavior without private music.

Tasks:

- create `tests/fixtures/rekordbox/clean-library.xml`
- create `missing-local-file.xml`
- create `streaming-placeholder.xml`
- create `playlist-ref-missing-track.xml`
- create `duplicate-track-id.xml`
- create `cue-loop.xml`
- create `unknown-cue-type.xml`
- create `duplicate-cue-bearing-survivor.xml`
- create `duplicate-multiple-cued-different-cues.xml`
- create `playlist-projection.xml`
- create `hotcue-slot-conflict.xml`
- create `bad-active-folder-reference.xml`
- create `audio-compatibility-fixtures/`
- create golden human reports
- create golden JSON reports

Exit criteria:

- every important report claim has a fixture
- contributors can add features by adding fixtures first

## Phase 3.5: Legacy Use-Case Coverage

Goal: ensure the public roadmap covers the real cleanup use cases without copying private scripts.

Source:

- [Legacy Script Audit](legacy-script-audit.md)

Tasks:

- convert each legacy use-case family into at least one synthetic fixture
- define match evidence types
- define confidence levels
- define report schemas for:
  - verification report
  - candidate plan
  - human decision sheet
  - apply manifest
  - post-apply audit
- document which legacy behaviors are intentionally postponed

Exit criteria:

- no private paths or private metadata are needed to explain the use cases
- every major script family maps to a module, command, fixture family, or explicit non-goal

## Phase 4: Snapshot Command

Goal: package a library's read-only state into a stable artifact.

Command:

```bash
djlib-doctor snapshot --rekordbox-xml export.xml --music-root ~/Music --out run/
```

Tasks:

- write `snapshot.json` (done)
- write `verification.txt` (done)
- write `verification.json` (done)
- write `missing-files.csv` (done)
- write `streaming-placeholders.csv` (done)
- write `cue-summary.csv` (done)
- write `playlist-summary.csv` (done)
- write `filesystem-inventory.csv` when `--music-root` is provided (done)
- include command metadata and timestamps (done)
- use portable artifact references in `snapshot.json` (done)
- add path redaction option for shareable snapshots (done)

Exit criteria:

- a DJ can share a snapshot directory without sharing music
- an agent can inspect snapshot JSON and propose next read-only analysis

## Phase 5: Plan Generation

Goal: propose actions without taking them.

Planned commands:

```bash
djlib-doctor plan missing-files --snapshot run/snapshot.json --out run/plan-missing-files.json # done
djlib-doctor plan duplicates --snapshot run/snapshot.json --out run/plan-duplicates.json # done
djlib-doctor plan duplicates --snapshot run/snapshot.json --out run/plan-duplicates-quality.json --collision-policy quality # done
djlib-doctor plan bad-paths --snapshot run/snapshot.json --out run/plan-bad-paths.json # done
djlib-doctor plan audio-compatibility --probe-csv run/audio-probes.csv --out run/plan-audio-compatibility.json # done
djlib-doctor plan audio-compatibility --probe-csv run/audio-probes.csv --out run/plan-wav-16.json --profile wav-16 # done
djlib-doctor plan cues --baseline baseline.xml --final final.xml --out run/plan-cues.json # done
djlib-doctor explain --plan run/plan-duplicates.json
djlib-doctor review --plan run/plan-duplicates.json --out run/review-decisions.json # done
djlib-doctor decision-sheet --plan run/plan-duplicates.json --out run/decision-sheet.csv # done
djlib-doctor apply-manifest --plan run/plan-duplicates.json --review-log run/review-decisions.json --only-reviewed --out run/apply-manifest.json # done
djlib-doctor schema --pretty # done
```

Tasks:

- define plan schema
- define confidence levels (done for missing-files)
- define human-review flags
- explain evidence per proposed action
- classify unsafe matches
- classify duplicate survivor cases (done)
- support duplicate collision policy choices (done)
- classify missing-file actions (done)
- classify hotcue/cue coverage issues (basic version done)
- classify bad path hygiene issues (done)
- classify audio compatibility probe issues (done)
- support audio compatibility profile choices and CLI overrides (done)
- export human decision sheet CSVs from plans (done)
- run interactive CLI review and write ingestible decision logs (done)
- export dry-run apply manifests from plans and optional review logs (done)
- expose report and CSV schema metadata from the CLI (done)
- keep all output read-only

Exit criteria:

- no plan applies changes
- every proposed action has evidence
- unsafe items are clearly marked for human review

## Phase 5.5: Verification Comparisons

Goal: compare baseline and final/planned libraries.

Tasks:

- compare material track representation (done by normalized artist/title)
- compare playlist projection and order (done by normalized artist/title)
- compare cue coverage (done by time tolerance)
- compare hotcue regression risk (done)
- compare bad path hygiene (done)
- compare local file missing status with opt-in file checks (done)

Exit criteria:

- users can prove a cleanup plan did not lose material tracks, playlist order, or cue timing work

## Phase 5.75: Serato Read-Only Porting Support

Goal: incorporate generalized lessons from the separate Rekordbox-to-Serato porting lab without importing that project or enabling live writes.

Commands:

```bash
djlib-doctor inspect serato --library-dir "/path/to/serato-library" --out run/inspect-serato # done
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --playlist "ROOT / My Playlist" --out run/rb-to-serato --verify-preview # done
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --playlists-file playlists.txt --summary-only --out run/unused # done
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --playlists-file playlists.txt --out run/rb-to-serato-batch # done
```

Tasks:

- add neutral library model shared by Rekordbox XML and future platform adapters (done)
- read Serato `root.sqlite` schema and row counts read-only (done)
- generate schema fingerprint for Serato inspection (done)
- write Serato legacy crate previews to run folders only (done)
- generate dry-run Rekordbox XML to Serato port manifests (done)
- support playlist-file batch planning (done)
- support summary-only planning before writing artifacts (done)
- verify single-crate preview order against the manifest (done)
- report raw cue rows, unique per-track cues, and Serato-writable cue slots (done)
- report Serato cue-tag capability by audio extension (done)
- warn on trim-only playlist matches and sanitized crate filename collisions (done)
- record managed crate namespace policy (done)
- map hotcue, memory cue, and loop intent for Serato (done)
- keep live Serato DB writing and audio-tag writing out of scope (done)

Exit criteria:

- no live Serato files are modified
- fixtures cover crate encoding, SQLite inspection, and dry-run port manifest generation
- docs clearly distinguish the separate porting lab from open-source `djlib-doctor`

## Phase 6: Codex Skill

Goal: make Codex discover the safe workflow.

Tasks:

- add `.agents/skills/djlib-doctor/SKILL.md` (done)
- front-load trigger terms in the skill description
- include read-only workflow steps
- include common prompts
- include safety boundaries
- include command recipes
- test with prompts like:
  - "verify my Rekordbox export"
  - "why are there more XML tracks than local files?"
  - "find missing files without changing anything"

Exit criteria:

- Codex implicitly selects the skill for relevant tasks
- explicit `$djlib-doctor` invocation works
- the skill does not encourage DB writes or file moves

## Phase 7: Codex Plugin

Goal: make the workflow installable for Codex users.

Tasks:

- create plugin folder (done)
- add `.codex-plugin/plugin.json` (done)
- package the `djlib-doctor` skill (done)
- add icons and metadata
- add local marketplace entry for private testing (repo skeleton done)
- test install from local marketplace
- later share with selected workspace users

Exit criteria:

- plugin appears in Codex plugin directory during private testing
- installed plugin exposes the skill
- README explains the plugin is optional and wraps the CLI workflow

## Phase 8: Claude Desktop Extension

Goal: make the read-only workflow easy for Claude Desktop users.

Boundary:

- allowed: Claude Desktop extension packaging
- not planned now: standalone MCP server product or generalized MCP API

Tasks:

- wait until CLI and JSON reports are stable
- define extension UX:
  - choose XML export
  - choose optional music root
  - run read-only verify
  - show/save report
- add extension manifest template (done)
- package private `.mcpb`
- test private install
- document install and troubleshooting
- submit to directory only after read-only workflow has real users

Exit criteria:

- private `.mcpb` can be installed by a trusted tester
- extension exposes only read-only workflow
- user can uninstall cleanly

## Phase 9: First Public Release

Goal: publish a useful read-only tool.

Tasks:

- scrub repo for private paths and data
- choose license
- finalize README
- finalize docs
- add changelog
- tag `v0.1.0`
- publish GitHub repo
- optionally publish PyPI package
- create short demo
- create launch issue list

Public release scope:

- Rekordbox XML verifier
- human reports
- JSON reports
- snapshot command if ready
- fixture corpus
- Codex guidance

Do not include write-capable features in the first public release.

## Phase 10: Post-Public Growth

Goal: grow carefully.

Tasks:

- collect fixture requests
- add adapters only when safety model is clear
- add plan generation
- add dry-run file operations
- add XML writer
- add DB writer last

Success metric:

- DJs trust the report before they trust the repair.
