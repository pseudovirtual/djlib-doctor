# Phase I Results

## Rekordbox 7.2.8 AAC/M4A Shift

Real-world validation against Rekordbox 7.2.8 confirmed that Rekordbox >=7 ignores AAC gapless metadata for this conversion path. A track converted to AAC/M4A is positioned later than the source in Rekordbox analysis, so the cue/beat shift is positive and `--cue-shift auto` remains the default.

Observed result:

- MP3-to-M4A: the analyzed beatgrid differed by a constant +21 ms across every beat.
- Example first-beat positions: MP3 at 25 ms, M4A at 46 ms.
- WAV-to-M4A: source decoder delay is 0, so the expected shift is the target AAC/M4A skip-samples delay, about ~23 ms.

Precision note: the MP3-to-M4A test measured target M4A skip-samples at about 23 ms, but the real net shift was +21 ms because the source MP3 carried about 2 ms of decoder delay. The correct automatic shift is net delay:

```text
shift_ms = target_decoder_delay_ms - source_decoder_delay_ms
```

Clamp negative results to 0. For lossless WAV/AIFF sources, source delay is 0.
The staged conversion manifest records `source_decoder_delay_ms`, `target_decoder_delay_ms`, and the resulting `cue_shift_ms`.
