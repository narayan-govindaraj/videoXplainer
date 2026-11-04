# VideoXplainer

**Your AI reads 4k tokens instead of 18k, and every claim comes with a quote you can check.**

[![ci](https://github.com/narayan-govindaraj/videoxplainer/actions/workflows/ci.yml/badge.svg)](https://github.com/narayan-govindaraj/videoxplainer/actions)
![license: MIT](https://img.shields.io/badge/license-MIT-blue)
![python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)

Most "YouTube summarizer" tools paste the whole transcript into your chat. That burns your context window, and nothing stops the model from inventing points the video never made.

videoxplainer sits between the video and your assistant (Claude Code, Claude Desktop, any agent that can run a command):

- **Condenses by chapter, to a token budget you choose.** Every chapter keeps a share, so the end of the video isn't dropped.
- **Makes claims checkable.** Ask for actions *with verbatim quotes*, then `videoxplainer verify` confirms each quote really appears in the video, and where.
- **Needs no API key and no LLM of its own.** Your assistant does the reading; videoxplainer does the plumbing. One `pipx install`, no Node, no compiler.

## See it work

A real run on a public 1-hour talk (59:48):

```text
$ videoxplainer fetch zjkBMFhNj_g --budget 4000 --mode summary

# [1hr Talk] Intro to Large Language Models
Andrej Karpathy | 59:48 | en (auto-captions)
sections: 21 (YouTube chapters)
note: condensed to ~3994 of ~17957 tokens (extractive, spread across sections)
---
## [00:20] LLM Inference
[00:29] ...
## [25:43] LLM Scaling Laws
[25:44] ...
## [46:14] Jailbreaks
[46:33] ...
---
TASK: for each "##" heading above write 1-2 sentences on its main point ...
```

About 17.9k tokens become about 4k, spread over all 21 chapters. Your assistant reads that and writes the chapter-by-chapter summary. No chapters on the video? videoxplainer detects topic shifts from the text instead.

Then check the model's work (illustrative output):

```text
$ videoxplainer verify VIDEO_ID claims.json
{ "checked": 3, "supported": 2, "weak": 0, "unsupported": 1,
  "items": [
    { "index": 0, "status": "supported",   "matched_at": "01:05", "link": "https://youtu.be/VIDEO_ID?t=65" },
    { "index": 1, "status": "supported",   "matched_at": "02:10", "link": "https://youtu.be/VIDEO_ID?t=130" },
    { "index": 2, "status": "unsupported" } ] }
```

Unsupported means the quote the model cited isn't in the video: drop or fix that point.

## How it compares

| | **videoxplainer** | [youtube-summarize](https://pypi.org/project/youtube-summarize/) (MCP) | [didntwatch](https://github.com/ewro/didntwatch) | [fabric](https://github.com/danielmiessler/fabric) | [martino-summarize](https://pypi.org/project/martino-summarize/) |
|---|---|---|---|---|---|
| Needs an LLM API key | **No** | No | No | Yes | Yes (bring your own) |
| You set a token budget | **Yes** | - | - | - | Yes (optional LLM prefilter) |
| Chapter-aware condensing | **Yes** | metadata only | - | - | - |
| Checks the model's quotes against the video | **Yes** | - | - | - | - |
| Windows install documented | Yes | Yes | no (Linux/macOS) | Yes | Yes |
| Sources beyond YouTube | local subtitle/transcript files | - | - | articles, files, audio/video files | **11+** |
| Speech-to-text fallback | - (roadmap) | - | - | Yes (OpenAI API) | **Whisper** |
| Runtime | Python 3.9+ | Python 3.13+, uv | Claude Code skill | Go binary | Python or Docker |

`-` means I found nothing in the README or code (I read each project's repository in November 2026). Found a mistake? Please open an issue.

Notes on the table:
- The closest thing to a token budget elsewhere is martino-summarize's optional prefilter (default: keep 35% of each chunk, scored by an LLM). fabric's `--maxTokens` and martino's `max-tokens` cap the *output*, not what your assistant has to read.
- didntwatch tells the model to stay grounded in the transcript (a prompt rule); nothing checks it afterwards. martino's "Fact Checker" prompt checks claims against outside sources, not quotes against the video.

Pick **martino-summarize** if you want a full self-hosted pipeline that calls its own LLM and covers many platforms. Pick **fabric** if you live in prompt "patterns". Pick **videoxplainer** if you want your own assistant to do the reading with the fewest tokens and verifiable claims.

## Install

```bash
pipx install videoxplainer
videoxplainer doctor              # checks your setup (`vxp` is a short alias for the same command)
```

Windows: `py -m pip install videoxplainer`, then run it as `py -m videoxplainer ...` if `videoxplainer` isn't on your PATH.
Until the first PyPI release: `pipx install git+https://github.com/narayan-govindaraj/videoxplainer`.

With Claude Code, run `videoxplainer install-skill` (it writes one file, `~/.claude/skills/videoxplainer/SKILL.md`, and tells you where), restart Claude Code, then paste a video link. Other agents: `videoxplainer install-skill --print` shows the instructions to paste into theirs. Claude Desktop needs an MCP server, which is on the roadmap.

## Use

Choose **what you see** with `--view`, and **what the assistant should do** with `--mode`:

| `--view` | You get |
|---|---|
| `chapters` (default) | condensed passages grouped under chapter / topic headings |
| `excerpts` | condensed key passages only, flat |
| `raw` | captions exactly as downloaded, unfiltered |

| `--mode` | Task appended for the assistant |
|---|---|
| `text` (default) | none, just the content |
| `summary` | a summary (one per chapter in the chapters view) |
| `actions` | evidence-backed actions, checkable with `videoxplainer verify` |

```bash
videoxplainer fetch "https://youtu.be/VIDEO_ID" --view chapters --mode summary --budget 4000
videoxplainer fetch VIDEO_ID --mode actions       # then: videoxplainer verify VIDEO_ID claims.json
videoxplainer fetch VIDEO_ID --view raw           # everything, untouched
videoxplainer search "pricing advice"             # across everything you've fetched
videoxplainer fetch weekly-sync.vtt --mode summary  # a meeting or podcast transcript on disk
```

**Your own transcripts.** Point `fetch` (and `verify`, `check`) at a `.srt`, `.vtt`, `.json3`, `.txt` or `.md` file: meeting exports, podcast transcripts, subtitles you downloaded. Text files with leading timestamps (`[00:12:30] ...`) keep them; files with none get timestamps estimated from word count, and the output says so. Nothing leaves your machine.

`--full` gives the complete cleaned transcript with no limit. `--refresh` re-downloads (once per video fetched before v0.2, to pick up chapter markers).

Something off on a video? Run `videoxplainer check <url>`: it tests the whole pipeline on that video (budget respected, every section represented, quotes verifiable) and its output makes a great bug report.

If YouTube asks you to prove you're not a bot: `--cookies-from-browser firefox` (Chrome/Edge cookie import is unreliable on Windows) or `--cookies-file cookies.txt`.

## Limits, honestly

- Online sources: YouTube only for now, and the video needs captions (no speech-to-text yet). Local files must already be text.
- Condensing is extractive and lossy by design. Use `--full` or `--view raw` when every word matters.
- Auto-detected sections are a heuristic. YouTube's own chapters are used whenever they exist. On two real talks with known chapters, detection from the text alone put 6 of 11 cuts within a minute of a real chapter start and recovered 7 of 25 real chapter starts; its headings are keyword lists (summary mode asks your assistant to rename them). Run `videoxplainer check <url>` to see how it does on your video.
- `verify` proves a quote exists in the video. It can't tell you the advice is good.
- Token counts are conservative estimates (about 4 characters per token for Latin text, heavier for other scripts).
- Works with any language written with spaces between words (tested on English, Hindi, Tamil text). Chinese and Japanese aren't word-segmented yet, so section detection and quote matching are weaker there.
- YouTube changes things; if caption downloads break, update yt-dlp first (`pip install -U yt-dlp`).
- Use it for your own research and respect creators' rights and YouTube's terms.

## Roadmap

- [x] v0.1 budgeted briefs, `verify`, local search
- [x] v0.2 chapter-aware condensing, three views, summary mode
- [x] v0.3 `install-skill`, local transcript files
- [ ] v0.4 `videoxplainer channel <url> --since 7d` digests, MCP server (Claude Desktop, Cursor)
- [ ] v0.5 ask your library with receipts, cross-video agreements/disagreements, optional free local speech-to-text (faster-whisper), more platforms via yt-dlp

## Credits and license

MIT. Built on [yt-dlp](https://github.com/yt-dlp/yt-dlp) (Unlicense) for caption retrieval. Developed with AI assistance (Claude).
