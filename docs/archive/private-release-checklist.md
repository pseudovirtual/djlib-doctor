# Private Release Checklist

Historical note: this checklist predates the public GitHub repo. Keep this archived file only for privacy-scrub context; do not use the private repo creation steps as current setup guidance.

Use this only as a privacy-scrub checklist before public releases or large documentation updates.

## Local Checks

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
rg "<private-username>|<private-folder>|<private-export-name>|<private-db-path>|<private-project-name>"
```

Review any matches before committing.

## Files

- [ ] `README.md` explains current status.
- [ ] `AGENTS.md` exists.
- [ ] `CONTRIBUTING.md` exists.
- [ ] `SECURITY.md` exists.
- [ ] `CHANGELOG.md` exists.
- [ ] `docs/legacy-script-audit.md` contains generalized use cases only.
- [ ] GitHub Actions test workflow exists.
- [ ] Issue templates exist.
- [ ] PR template exists.
- [ ] `LICENSE` exists.

## Privacy

- [ ] No real Rekordbox exports.
- [ ] No real music files.
- [ ] No private artist/title metadata from the source cleanup project.
- [ ] No live DB paths.
- [ ] No one-off playlist names or TrackID overrides from private work.
- [ ] No credentials.

## GitHub

Current repository: `pseudovirtual/djlib-doctor`
