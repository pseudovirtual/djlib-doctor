# Rekordbox XML Concepts

This page explains the minimum Rekordbox XML concepts `djlib-doctor` needs users and contributors to understand.

## Collection Tracks

Collection tracks live under:

```xml
<COLLECTION>
  <TRACK TrackID="1" ... />
</COLLECTION>
```

These are library records.

## Playlist References

Playlist entries can also look like tracks:

```xml
<PLAYLISTS>
  <NODE Name="Playlist">
    <TRACK Key="1" />
  </NODE>
</PLAYLISTS>
```

These are references to collection tracks, not separate collection records.

## Local Files

Local files usually have `Location` values that point to filesystem paths:

```xml
Location="file://localhost/Users/example/Music/track.aiff"
```

## Streaming Placeholders

Some records refer to streaming services or placeholders:

```xml
Location="file://localhostsoundcloud:tracks:123456"
```

These should not be reported as missing local music files.

## Cues

Cues appear as `POSITION_MARK` rows.

Memory cue:

```xml
<POSITION_MARK Type="0" Start="12.345" Num="-1" />
```

Hotcue A:

```xml
<POSITION_MARK Type="0" Start="24.000" Num="0" />
```

Loop:

```xml
<POSITION_MARK Type="4" Start="48.000" End="56.000" Num="1" />
```

## Track Metadata And BeatGrid

`djlib-doctor` parses common collection metadata from `TRACK` attributes:

- `AverageBpm`
- `Tonality`
- `Colour` / `Color`
- `Rating`
- `Comments`

Beatgrid rows appear as `TEMPO` children:

```xml
<TEMPO Inizio="0.000" Bpm="124.50" Metro="4/4" Battito="1" />
```

Rekordbox-to-Serato port manifests carry parsed track metadata today. BeatGrid rows are parsed and reported with an explicit unsupported status until BeatGrid writing is implemented.

## Why Counts Can Look Confusing

A Rekordbox export can contain:

- collection records
- playlist references
- local file-backed records
- streaming placeholders

Those are different categories. `djlib-doctor` reports them separately so users do not mistake playlist references or streaming placeholders for missing local files.
