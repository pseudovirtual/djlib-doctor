# Feature List

`djlib-doctor` is read-only first. Write-capable workflows exist only as staged manifests with backups, hashes, and exact confirmation tokens.

## Available

- Rekordbox XML verification with text and JSON reports.
- Collection tracks counted separately from playlist references.
- Local files, streaming placeholders, and unknown locations classified separately.
- Memory cues, hotcues, cue loops, and loop end times parsed.
- Snapshot directories with redacted sharing mode.
- Plans for missing files, duplicates, cue coverage, bad paths, and audio compatibility.
- Local file fingerprinting, folder fingerprint manifests, and two-track similarity comparison.
- Duplicate collision policies: `cue-safe`, `quality`, and `keep-both`.
- Interactive CLI review logs and optional CSV decision sheets.
- Dry-run apply manifests generated from reviewed plans.
- Baseline/final export comparison.
- Port certification reports for migration previews and staged artifacts.
- Read-only Serato `root.sqlite` inspection.
- Dry-run Rekordbox-to-Serato crate manifests and preview crates.
- Dry-run Serato-to-Rekordbox port manifests with Rekordbox XML representation and fixture-backed cue rows for staged DB import work.
- Migration scopes for single tracks, playlists/crates, multiple playlists, and whole collections.
- Transfer modes for `full`, `cues-only`, and `match-only` workflows.
- Staged Serato library installs through `stage serato` and `install serato-stage`.
- Staged Serato audio tag writes through `stage serato-tags` and `install serato-tags`.
- Staged file copy, move, delete, and conversion operations through `stage file-ops` and `install file-ops`.
- Staged Rekordbox DB operations through copied `master.db`, staged hashes, backups, and `install rekordbox-db`.
- Config files for common user paths.
- Codex skill, Claude guidance, and plugin-template metadata.

## Main Commands

```bash
djlib-doctor verify export.xml
djlib-doctor snapshot --rekordbox-xml export.xml --music-root ~/Music --out run/
djlib-doctor plan missing-files --snapshot run/snapshot.json --out run/missing.json
djlib-doctor plan duplicates --snapshot run/snapshot.json --out run/dupes.json
djlib-doctor plan audio-compatibility --probe-csv probes.csv --out run/audio.json
djlib-doctor fingerprint compare old.wav new.aiff --out run/track-compare.json
djlib-doctor fingerprint scan ~/Music --out run/fingerprints.json --redact-paths
djlib-doctor review --plan run/missing.json --out run/review.json
djlib-doctor compare exports --baseline before.xml --final after.xml
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --playlist "ROOT / Set" --out run/port
djlib-doctor certify rb-to-serato --port-manifest run/port/port-manifest.json --out run/port/certification.json
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --track-id 123 --transfer-mode cues-only --out run/track
djlib-doctor port serato-to-rb --serato-library-dir Library --collection --collection-root ~/Music --out run/rb
djlib-doctor certify serato-to-rb --port-manifest run/rb/port-manifest.json --out run/rb/certification.json
djlib-doctor migrate rb-to-serato --rekordbox-xml export.xml --playlist "ROOT / Set" --out run/migrate
```

## Safety Guarantees

- Streaming placeholders are not treated as missing local files.
- Cue metadata is preserved as creative work and never discarded silently.
- Plans do not apply changes.
- Install commands verify tokens, staged hashes, source hashes, backups, and app/sidecar checks where relevant.
- Tests use synthetic fixtures only.
- Certification reports are read-only scorecards and do not install staged changes.

## Not Yet Public-Release Ready

- More Rekordbox DB schema adapters and playlist/cue table variants are needed for broader real-world coverage.
- Claude Desktop extension packaging is still a template.
- PyPI publishing uses tag-triggered GitHub Actions and still requires repository-side trusted publishing configuration.
- More real-world Serato fixture validation is needed before broad public claims.
