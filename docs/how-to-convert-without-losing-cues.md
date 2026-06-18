# Convert Without Losing Cues

Use this workflow when you want Rekordbox to point at a converted file while preserving cues, loops, and beatgrid timing as safely as the current staged workflow supports.

## 1. Prepare Operations

Create `run/convert.json` with one operation per track:

```json
{
  "operations": [
    {
      "track_id": "123",
      "source": "/Music/Old/Track.wav",
      "target": "/Music/New/Track.m4a",
      "preset": "aac-m4a-256",
      "anlz_files": ["/Rekordbox/share/PIONEER/USBANLZ/ANLZ0001.DAT", "/Rekordbox/share/PIONEER/USBANLZ/ANLZ0001.EXT"]
    }
  ]
}
```

## 2. Stage

```bash
djlib-doctor stage rekordbox-convert --db /path/to/rekordbox/master.db --operations run/convert.json --stage-dir run/rekordbox-convert --cue-shift auto
```

`--cue-shift auto` measures decoder delay with `ffprobe`, then shifts `master.db` cues, ANLZ PCOB/PCO2 cues, and ANLZ PQTZ/PQT2 beatgrid millisecond fields by the net target-minus-source offset. Rekordbox 7.2.8 validation confirmed Rekordbox >=7 ignores AAC gapless metadata in this path: MP3-to-M4A needed a positive +21 ms shift, while WAV-to-M4A is expected to use the full target delay of about ~23 ms. Use `--cue-shift none` only after validating that your Rekordbox/player path honors gapless metadata without stored-position shifts.

## 3. Inspect And Install

Inspect `run/rekordbox-convert/rekordbox-convert-stage-manifest.json`, confirm paths and hashes, close Rekordbox, then install with the printed token:

```bash
djlib-doctor install rekordbox-convert --stage-dir run/rekordbox-convert --db /path/to/rekordbox/master.db --confirm-token INSTALL_REKORDBOX_CONVERT:...
```

Install verifies the token, DB hashes, source audio hashes, staged audio hashes, ANLZ hashes, backups, sidecars, and that Rekordbox is closed before writing.
