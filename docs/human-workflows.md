# Human Workflows

This document describes how different people should experience `djlib-doctor`.

## DJ With Terminal Comfort

Goal: check whether a Rekordbox export is healthy.

Workflow:

1. Export XML from Rekordbox.
2. Run:

   ```bash
   djlib-doctor verify ~/Desktop/rekordbox-export.xml
   ```

3. Read the report.
4. If there are missing files, inspect the missing list.
5. If there are streaming placeholders, understand that they are not local-file failures.
6. Save the report before making manual changes.

The tool should avoid jargon when possible. It should say "playlist references" and then explain that those are playlist entries pointing at collection tracks.

## DJ Using Codex

Goal: let Codex help interpret the library safely.

Workflow:

1. Open the project or a folder containing the XML export in Codex.
2. Ask:

   ```text
   Use djlib-doctor to verify my Rekordbox XML export. Stay read-only.
   ```

3. Codex reads `AGENTS.md`.
4. Codex runs the verifier.
5. Codex summarizes the result in normal DJ language.
6. Codex suggests next read-only steps only.

Future plugin workflow:

1. Install the `djlib-doctor` Codex plugin.
2. Ask the same natural-language question.
3. Codex invokes the packaged skill and uses the CLI.

## DJ Using Claude Desktop

Goal: use a friendly desktop chat interface.

Local workflow:

1. Clone and install the project locally.
2. Open the repo or docs with Claude.
3. Ask Claude to follow `AGENTS.md`.
4. Have Claude explain commands to run, or run them if it has local tool access.

Future extension workflow:

1. Install the `djlib-doctor` Claude Desktop extension package.
2. Configure allowed folders, such as the Desktop export folder and Music folder.
3. Ask:

   ```text
   Check my Rekordbox export and explain whether any local files are missing.
   ```

4. Claude uses the packaged read-only workflow.
5. Claude returns a plain-English summary and points to the saved report.

The extension should expose write-capable actions only through implemented dry-run, stage, and token-gated install flows.

## Developer Contributor

Goal: add behavior safely.

Workflow:

1. Clone the repo.
2. Create a branch.
3. Run:

   ```bash
   PYTHONPATH=src python3 -m unittest discover -s tests
   ```

4. Add or update synthetic fixtures.
5. Implement the parser, verifier, report, or planner change.
6. Add tests.
7. Run the test suite again.
8. Update docs if user-visible behavior changed.
9. Open a pull request.

Good first tasks:

- add fixtures
- improve report wording
- add JSON output
- add report schema docs
- add playlist reference validation
- add unknown location examples
- turn a legacy use-case family into a synthetic fixture
- add a golden report for a fixture

Avoid as early tasks:

- database writes
- file deletion
- automatic duplicate merging
- real music fixtures

## Maintainer Auditing Legacy Coverage

Goal: make sure the public project captures real cleanup lessons without leaking private details.

Workflow:

1. Review [Legacy Script Audit](legacy-script-audit.md).
2. Pick one use-case family.
3. Add a synthetic fixture that captures the behavior.
4. Add expected human and JSON report examples.
5. Update the feature list or execution plan if the use case needs a module or command.
6. Do not copy private paths, playlist names, TrackIDs, or one-off overrides.

## Maintainer

Goal: improve the public project without surprising users.

Workflow:

1. Keep docs, license, tests, and safety language current.
2. Cut internal milestones with changelog entries.
3. Use synthetic fixtures only.
4. Review every new command for safety language.
5. Prefer one boring release over many flashy claims.
6. Keep the default first-run experience read-only.

The first public impression should be:

> This tool understands my DJ library and is careful with it.
