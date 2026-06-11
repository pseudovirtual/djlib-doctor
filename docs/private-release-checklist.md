# Private Release Checklist

Use this before pushing to the private GitHub repository.

## Local Checks

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
rg "<private-username>|<private-folder>|<private-export-name>|<private-db-path>|<private-project-name>"
```

Review any matches before committing.

## Files

- [ ] `README.md` explains current status.
- [ ] `AGENTS.md` exists.
- [ ] `CLAUDE.md` exists.
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

Planned repository:

```text
pseudovirtual/djlib-doctor
```

Create privately when ready:

```bash
gh repo create pseudovirtual/djlib-doctor --private --source . --remote origin --push
```
