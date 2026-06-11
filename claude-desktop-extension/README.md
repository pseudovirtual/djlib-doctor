# Claude Desktop Extension Skeleton

This folder documents the future Claude Desktop extension package for `djlib-doctor`.

Current status: **not installable yet**.

Claude Desktop `.mcpb` extensions package a local MCP server plus `manifest.json`. The current project intentionally does not build a standalone MCP server yet, so this folder is a packaging placeholder and checklist rather than a working `.mcpb`.

Allowed near-term work:

- keep the CLI workflow stable
- keep JSON report schemas stable
- design the extension user experience
- document permissions and folder choices

Not allowed yet:

- exposing file moves, conversion, quarantine, deletion, XML writing, or DB writing
- claiming the extension is installable
- submitting to any public directory

Future user flow:

1. Install the private `.mcpb`.
2. Configure allowed folders for Rekordbox XML exports and optional music roots.
3. Ask Claude to verify or snapshot an export.
4. Claude runs read-only verification through the packaged local server.
5. Claude explains saved reports in DJ-friendly language.

Current source note:

- Claude Desktop MCPB docs say `.mcpb` is a zip archive containing a local MCP server and `manifest.json`, with stdio transport and Node.js recommended.
