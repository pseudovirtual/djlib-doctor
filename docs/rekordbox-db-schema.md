# Rekordbox DB Schema Reference

This page records the Rekordbox `master.db` schema subset targeted by `djlib-doctor` generated fixtures and staged imports.

Source of truth: pyrekordbox `pyrekordbox.db6.tables`, especially `StatsFull`, `DjmdContent`, `DjmdCue`, `DjmdPlaylist`, and `DjmdSongPlaylist`. `djlib-doctor` should use pyrekordbox for encrypted Rekordbox 6/7 DB behavior instead of inventing a parallel ORM.

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
| `OutMsec` | integer | Loop end in milliseconds, or `-1`/non-positive when no loop end exists. |
| `Kind` | integer | Real read path uses `0` for memory cues and `>=1` for hotcues; hotcue slot is `Kind - 1`. |
| `is_hot_cue` | boolean | Real read path hotcue flag. |
| `is_memory_cue` | boolean | Real read path memory cue flag. |
| `Name` | text | Cue label. |
| `rb_local_usn` | integer | Local update sequence marker. |
| `created_at` | text datetime | Fixture timestamp. |
| `updated_at` | text datetime | Fixture timestamp. |

Cue semantics must remain explicit: cue vs loop type, loop end, hotcue slot, and label must not be silently dropped.
The reader follows the live Rekordbox 7 schema: hotcue-vs-memory comes from `is_hot_cue`/`is_memory_cue` and `Kind`, while loop-vs-point-cue comes from `OutMsec > 0`.

## Encryption Boundary

Rekordbox 6/7 `master.db` files are SQLCipher databases. The generated encrypted fixture path uses the public SQLCipher key exposed by pyrekordbox and SQLCipher4 settings. Tests skip clearly when the SQLCipher backend cannot import.

pyrekordbox and SQLCipher are default dependencies because Rekordbox DB support is core scope. Runtime failures must distinguish a missing SQLCipher backend from a key-locked or unsupported `master.db`. Real app acceptance remains a manual smoke test.

`sqlcipher3-wheels` stays a core dependency, but its prebuilt wheel coverage is platform-dependent. The supported CI matrix is Ubuntu x64, Windows x64, and current GitHub macOS arm64 runners on Python 3.9 and 3.13. Prebuilt SQLCipher wheels are not available for every platform/Python combination; the known gap is Intel/x86_64 macOS on Python 3.13, where `pip install` can fail while trying to build SQLCipher. Recommended workarounds are Apple Silicon macOS or Python <=3.12 on Intel macOS.
