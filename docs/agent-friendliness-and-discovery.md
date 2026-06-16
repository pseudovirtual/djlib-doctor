# Agent Friendliness And Discovery Plan

`djlib-doctor` should be easy for humans first and easy for agents second.

Near-term scope:

- excellent CLI
- excellent human docs
- machine-readable reports
- Codex repo guidance
- Codex skill/plugin packaging
- Claude Desktop extension packaging later

Explicitly out of near-term scope:

- standalone MCP server
- generalized MCP API
- direct live-write agent tools

Claude Desktop extensions may still require extension-specific packaging mechanics, but the project should not design around MCP as the core product yet. The CLI and report schemas should remain the source of truth.

## Discovery Strategy

Models do not magically know a new open-source tool exists. Discovery has to happen through surfaces the model already reads.

## Human-First Surfaces

These help DJs and developers before any agent integration exists:

- `README.md`
- `docs/feature-list.md`
- `docs/human-workflows.md`
- `docs/safety.md`
- `docs/reports.md`
- `docs/rekordbox-xml-concepts.md`
- `examples/`

The README should include phrases users will actually ask:

- "verify a Rekordbox XML export"
- "find missing files"
- "check streaming placeholders"
- "preserve hotcues and memory cues"
- "dry-run DJ library cleanup"
- "agent-friendly Rekordbox library verifier"

## Codex Discovery

Codex can discover repo instructions from `AGENTS.md`, repo skills from `.agents/skills`, and packaged workflows from plugins.

Recommended staged approach:

1. Keep root `AGENTS.md` accurate.
2. Add `.agents/skills/djlib-doctor/SKILL.md` once the workflow stabilizes. (done)
3. Package that skill as a Codex plugin when the public workflow is useful. (repo skeleton done)
4. Add a repo or personal marketplace entry for testing. (repo marketplace skeleton done)
5. Later, share the plugin with selected users or publish through the appropriate Codex distribution path.

Skill description should front-load trigger terms:

```md
---
name: djlib-doctor
description: Verify and plan safe cleanup for Rekordbox DJ libraries using djlib-doctor; use for Rekordbox XML exports, missing files, streaming placeholders, hotcues, memory cues, playlist references, and read-only DJ library reports.
---
```

Skill behavior:

- read `AGENTS.md`
- run verifier commands
- explain reports in DJ language
- suggest read-only analysis first
- use write-capable commands only when an implemented stage/install workflow exists and the user approves it
- never present XML preview as the final Serato-to-Rekordbox write workflow; use staged `master.db` import/install language

## Claude Desktop Discovery

Claude users should get two layers:

1. `AGENTS.md` and the README for project context when working in the repo.
2. A Claude Desktop extension package later, once the CLI and JSON reports are stable.

Near-term Claude workflow:

- user opens repo or docs in Claude
- Claude reads `AGENTS.md`
- Claude helps run or interpret CLI output

Future extension workflow:

- user installs a local or published `.mcpb` package
- user configures allowed folders
- extension runs the read-only verifier workflow
- Claude explains the saved report

The extension should expose write-capable actions only through mature approval-bound stage/install commands. It should never expose direct live file, XML, or DB mutation.

Current repo status:

- `claude-desktop-extension/README.md` documents the extension boundary.
- `claude-desktop-extension/manifest.template.json` is a template only.
- It is intentionally not packaged as `.mcpb` yet because Claude Desktop MCPB packages require a local MCP server, and the current project scope excludes building one.

## Machine-Readable Reports

Reports are the bridge between CLI and agents.

Add:

- `--json`
- schema version
- stable exit codes
- warnings array
- failures array
- next actions array

Agents should inspect JSON reports instead of scraping human prose.

## Public Discoverability

Use ordinary open-source distribution first:

- public GitHub repo under `pseudovirtual/djlib-doctor`
- GitHub topics: `rekordbox`, `dj`, `music-library`, `hotcues`, `agent-tools`, `codex`, `claude-desktop`
- PyPI package eventually: `djlib-doctor`
- short demo report
- `llms.txt` and `llms-full.txt` later
- example prompts for Codex and Claude
- issues labeled `good first issue`, `fixture needed`, and `safety`

Suggested tagline:

> Read-only first, cue-safe DJ library verification and cleanup planning for Rekordbox exports.

## Source Notes

- Codex manual, fetched 2026-06-05: skills are reusable workflows, plugins are the installable distribution unit, and Codex discovers repo instructions through `AGENTS.md`.
- Claude Help Center, March 16, 2026: Claude Desktop supports desktop extensions, custom `.mcpb` installation, directory browsing, and extension packaging.
