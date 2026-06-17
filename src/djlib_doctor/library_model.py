from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .cues import CueKind, CueType
from .locations import LocationKind
from .rekordbox_xml import RekordboxLibrary


@dataclass(frozen=True)
class LibraryCue:
    kind: str
    cue_type: str
    start_seconds: float
    end_seconds: float | None = None
    slot: int | None = None
    label: str = ""

    @property
    def start_ms(self) -> int:
        return int(round(self.start_seconds * 1000))

    @property
    def end_ms(self) -> int | None:
        if self.end_seconds is None:
            return None
        return int(round(self.end_seconds * 1000))


@dataclass(frozen=True)
class LibraryTrack:
    source_id: str
    path: Path | None
    title: str
    artist: str = ""
    album: str = ""
    genre: str = ""
    key: str = ""
    bpm: float | None = None
    length_seconds: int | None = None
    comments: str = ""
    color: str = ""
    rating: int | None = None
    beatgrid: tuple[dict[str, object], ...] = field(default_factory=tuple)
    location_kind: str = ""
    format: str = ""
    cues: tuple[LibraryCue, ...] = field(default_factory=tuple)

    @property
    def serato_portable_id(self) -> str:
        if self.path is None:
            return ""
        return str(self.path).replace("\\", "/").lstrip("/")


@dataclass(frozen=True)
class LibraryPlaylist:
    source_id: str
    name: str
    track_ids: tuple[str, ...]


@dataclass(frozen=True)
class Library:
    source: str
    tracks: tuple[LibraryTrack, ...]
    playlists: tuple[LibraryPlaylist, ...]

    def track_by_id(self) -> dict[str, LibraryTrack]:
        return {track.source_id: track for track in self.tracks}


def rekordbox_xml_to_library(library: RekordboxLibrary) -> Library:
    tracks = tuple(
        LibraryTrack(
            source_id=track.track_id,
            path=track.path,
            title=track.name or "",
            artist=track.artist or "",
            key=track.key,
            bpm=track.bpm,
            length_seconds=None,
            comments=track.comments,
            color=track.color,
            rating=track.rating,
            beatgrid=track.beatgrid,
            location_kind=track.location_kind.value,
            format=track.format or "",
            cues=tuple(
                LibraryCue(
                    kind=_cue_kind(cue.kind),
                    cue_type=_cue_type(cue.cue_type),
                    start_seconds=cue.start,
                    end_seconds=cue.end,
                    slot=cue.slot,
                    label=cue.name or cue.hotcue_label or "",
                )
                for cue in track.cues
            ),
        )
        for track in library.tracks
    )
    playlists = tuple(
        LibraryPlaylist(
            source_id=playlist.name,
            name=playlist.name,
            track_ids=playlist.entries,
        )
        for playlist in library.playlists
    )
    return Library(source="rekordbox_xml", tracks=tracks, playlists=playlists)


def local_file_tracks(library: Library) -> tuple[LibraryTrack, ...]:
    return tuple(
        track
        for track in library.tracks
        if track.location_kind == LocationKind.LOCAL_FILE.value and track.path is not None
    )


def _cue_kind(kind: CueKind) -> str:
    return kind.value


def _cue_type(cue_type: CueType) -> str:
    return cue_type.value
