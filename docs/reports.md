# Reports And Manifests

Reports are meant for both humans and agents. They should be stable, explicit, and safe to inspect before any staged write.

## Report Types

- `verification`: Rekordbox XML health check.
- `snapshot`: artifact index plus verification summary.
- `plan`: review actions for missing files, duplicates, cues, bad paths, or audio compatibility.
- `review-log`: interactive human decisions.
- `apply-manifest`: dry-run operations derived from a reviewed plan.
- `compare`: baseline/final export diff.
- `port-manifest`: dry-run migration plan.
- `*-stage-manifest`: staged files plus hashes and install token.
- `*-install-report`: backup paths and post-install verification.

## Common Fields

- `schema_version`
- `mode`
- `summary`
- `safety`
- `operations` or `tracks`
- `hashes`
- `source_hashes` where live source drift matters
- `install_token` for staged writes

## Rules

- Plans do not apply changes.
- Stage manifests describe exactly what will be installed later.
- Install reports must include backup paths and verification results.
- Schema changes should update `djlib-doctor schema --pretty` and tests.
