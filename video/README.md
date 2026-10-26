# Northstar demo video

`northstar-wind-desk-demo.mp4` is a 6.92-minute caption-led guide with two sections: a client pilot walkthrough and an internal technical handover. The guide is silent; the complete talk track appears on screen and is provided as an SRT transcript. It has two sections under five minutes each. The original script is in `source/narration.json`; the build creates intermediate slide renders in `rendered/`.

The chart and metric values shown in slides are explicitly illustrative, not January Elexon observations. The live app itself loads Elexon data when the backend has network access. This avoids presenting fabricated numbers as measured pilot findings.

Rebuild on macOS with the system `say` command and FFmpeg:

```bash
python3 video/source/build_video.py
```
