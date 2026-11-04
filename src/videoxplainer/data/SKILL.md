---
name: videoxplainer
description: Use when the user shares a YouTube link or a transcript/subtitle file and wants key points, a summary, chapter notes, or action items without watching or reading it all.
allowed-tools:
  - Bash(videoxplainer:*)
  - Bash(vxp:*)
  - Bash(py -m videoxplainer:*)
---

# videoxplainer

Run `videoxplainer fetch "<url or file path>"` (on Windows without PATH: `py -m videoxplainer fetch ...`). Files can be .srt, .vtt, .txt. Choose by request:

- summary or chapter notes: `--view chapters --mode summary`
- action items: `--mode actions`, then follow its TASK and check quotes with `videoxplainer verify <video_id or file> <claims.json>`
- exact wording or search inside the video: `--view raw` (large; only when asked)
- long or dense video: add `--budget 6000`; complete text only if asked: `--full`

Follow the TASK block in the output. If it says the text was condensed, say so. Present timestamps as links when the output gives a link. If the command reports no captions or a bot check, relay the message plainly and offer to read pasted text instead.
