# Rekordbox DB Schema Reference

This page records the Rekordbox `master.db` schema subset targeted by `djlib-doctor` generated fixtures and staged imports.

Source of truth: pyrekordbox `pyrekordbox.masterdb.models`, especially `StatsFull`, `DjmdContent`, and `DjmdCue`. `djlib-doctor` should use pyrekordbox for broader encrypted Rekordbox 6/7 DB behavior instead of inventing a parallel ORM.

## Scope

Current support is intentionally narrow:

- generated fixture table: `djmdContent`
- generated fixture table: `djmdCue`
- staged import target: copied `master.db`
- write boundary: `stage rekordbox-db-import` or `stage rekordbox-db`, then `install rekordbox-db`

No live Rekordbox database is written directly.

## Shared StatsFull Bookkeeping

pyrekordbox models use a shared `StatsFull` shape for many tables. Generated rows should preserve these fields when present:

| Column | Type Family | Purpose |
| --- | --- | --- |
| `ID` | text/integer id | Primary key for the row. |
| `UUID` | text | Stable row UUID. |
| `rb_data_status` | integer | Rekordbox data status. |
| `rb_local_data_status` | integer | Local data status. |
| `rb_local_deleted` | small integer | Local deletion flag. |
| `rb_local_synced` | small integer | Local sync flag. |
| `usn` | big integer | Update sequence number. |
| `rb_local_usn` | big integer | Local update sequence number. |
| `created_at` | text datetime | Creation timestamp. |
| `updated_at` | text datetime | Last update timestamp. |

When `djlib-doctor` writes real Rekordbox rows through pyrekordbox, USN/UUID bookkeeping should be delegated to pyrekordbox where possible.

## `djmdContent`

`djmdContent` stores collection track rows. The current fixture/import subset is:

| Column | Type Family | Current Use |
| --- | --- | --- |
| `ID` | primary key | Track row identity. |
| `UUID` | text | Fixture bookkeeping. |
| `FolderPath` | text | Folder portion of the local path. |
| `FileNameL` | text | Filename portion of the local path. |
| `Title` | text | Track title. |
| `ArtistName` | text | Artist display name in fixture/import schema. |
| `AlbumName` | text | Album display name in fixture/import schema. |
| `GenreName` | text | Genre display name in fixture/import schema. |
| `KeyName` | text | Musical key display name. |
| `BPM` | real | Average BPM. |
| `Length` | integer | Track length in milliseconds. |
| `rb_local_usn` | integer | Local update sequence marker. |
| `created_at` | text datetime | Fixture timestamp. |
| `updated_at` | text datetime | Fixture timestamp. |

Broader pyrekordbox `DjmdContent` relationships such as artist, album, genre, key, color, and file tables are planned adapter work, not implicit current support.

## `djmdCue`

`djmdCue` stores cue and loop rows for the current fixture/import path:

| Column | Type Family | Current Use |
| --- | --- | --- |
| `ID` | primary key | Cue row identity. |
| `UUID` | text | Fixture bookkeeping. |
| `ContentID` | foreign key/id | Parent `djmdContent.ID`. |
| `InMsec` | integer | Cue or loop start in milliseconds. |
| `OutMsec` | integer/null | Loop end in milliseconds, null for normal cues. |
| `Kind` | integer | `0` for cue, `4` for loop in current importer. |
| `HotCue` | integer | Hotcue slot or `-1` for memory cue. |
| `Name` | text | Cue label. |
| `rb_local_usn` | integer | Local update sequence marker. |
| `created_at` | text datetime | Fixture timestamp. |
| `updated_at` | text datetime | Fixture timestamp. |

Cue semantics must remain explicit: cue vs loop type, loop end, hotcue slot, and label must not be silently dropped.

## Encryption Boundary

Rekordbox 6/7 `master.db` files are SQLCipher databases. The generated encrypted fixture path uses the public SQLCipher key exposed by pyrekordbox and SQLCipher4 settings. Tests skip clearly when `djlib-doctor[rekordbox]` dependencies are not installed.
