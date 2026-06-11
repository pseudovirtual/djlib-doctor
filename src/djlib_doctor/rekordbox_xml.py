from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional
import xml.etree.ElementTree as ET

from .cues import Cue, parse_cue_num, parse_cue_type, parse_position
from .locations import LocationKind, parse_location


@dataclass(frozen=True)
class Track:
    track_id: str
    name: Optional[str]
    artist: Optional[str]
    location: Optional[str]
    location_kind: LocationKind
    path: Optional[Path]
    format: Optional[str]
    cues: tuple[Cue, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PlaylistRef:
    key: str
    playlist: str = ""


@dataclass(frozen=True)
class Playlist:
    name: str
    entries: tuple[str, ...]


@dataclass(frozen=True)
class RekordboxLibrary:
    tracks: tuple[Track, ...]
    playlist_refs: tuple[PlaylistRef, ...]
    playlists: tuple[Playlist, ...] = field(default_factory=tuple)

    def track_by_id(self) -> dict[str, Track]:
        return {track.track_id: track for track in self.tracks}


def parse_rekordbox_xml(path: str | Path) -> RekordboxLibrary:
    root = ET.parse(path).getroot()

    collection = root.find("COLLECTION")
    tracks = tuple(_parse_track(track) for track in collection.findall("TRACK")) if collection is not None else ()

    playlist_root = root.find("PLAYLISTS")
    playlist_refs = tuple(_iter_playlist_refs(playlist_root)) if playlist_root is not None else ()
    playlists = tuple(_iter_playlists(playlist_root)) if playlist_root is not None else ()

    return RekordboxLibrary(tracks=tracks, playlist_refs=playlist_refs, playlists=playlists)


def _parse_track(element: ET.Element) -> Track:
    location = element.attrib.get("Location")
    kind, local_path = parse_location(location)
    cues = tuple(_parse_position_mark(mark) for mark in element.findall("POSITION_MARK"))

    return Track(
        track_id=element.attrib.get("TrackID", ""),
        name=element.attrib.get("Name"),
        artist=element.attrib.get("Artist"),
        location=location,
        location_kind=kind,
        path=local_path,
        format=element.attrib.get("Kind"),
        cues=cues,
    )


def _parse_position_mark(element: ET.Element) -> Cue:
    kind, slot = parse_cue_num(element.attrib.get("Num"))
    cue_type = parse_cue_type(element.attrib.get("Type"))

    end = None
    if "End" in element.attrib:
        end = parse_position(element.attrib.get("End"))

    return Cue(
        kind=kind,
        cue_type=cue_type,
        start=parse_position(element.attrib.get("Start")),
        end=end,
        slot=slot,
        name=element.attrib.get("Name"),
        color=element.attrib.get("Red"),
    )


def _iter_playlist_refs(root: Optional[ET.Element]) -> Iterable[PlaylistRef]:
    if root is None:
        return
    yield from _walk_playlist_refs(root)


def _walk_playlist_refs(node: ET.Element, names: tuple[str, ...] = ()) -> Iterable[PlaylistRef]:
    name = node.attrib.get("Name")
    path = names + (name,) if name else names
    if node.attrib.get("Type") == "1":
        playlist = " / ".join(path)
        for element in node.findall("TRACK"):
            key = element.attrib.get("Key")
            if key is not None:
                yield PlaylistRef(key=key, playlist=playlist)
    for child in node.findall("NODE"):
        yield from _walk_playlist_refs(child, path)


def _iter_playlists(root: Optional[ET.Element]) -> Iterable[Playlist]:
    if root is None:
        return
    yield from _walk_playlists(root)


def _walk_playlists(node: ET.Element, names: tuple[str, ...] = ()) -> Iterable[Playlist]:
    name = node.attrib.get("Name")
    path = names + (name,) if name else names
    if node.attrib.get("Type") == "1":
        playlist = " / ".join(path)
        yield Playlist(name=playlist, entries=tuple(element.attrib.get("Key", "") for element in node.findall("TRACK")))
    for child in node.findall("NODE"):
        yield from _walk_playlists(child, path)
