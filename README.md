<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/narayan-govindaraj/videoXplainer/main/docs/brand/logo-lockup-dark.png">
    <img src="https://raw.githubusercontent.com/narayan-govindaraj/videoXplainer/main/docs/brand/logo-lockup-light.png" alt="VideoXplainer" width="440">
  </picture>
</p>

**Your AI reads 4k tokens instead of 18k, and every claim comes with a quote you can check.**

[![ci](https://github.com/narayan-govindaraj/videoXplainer/actions/workflows/ci.yml/badge.svg)](https://github.com/narayan-govindaraj/videoXplainer/actions)
![license: MIT](https://img.shields.io/badge/license-MIT-blue)
![python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![platforms: Windows | macOS | Linux](https://img.shields.io/badge/platforms-Windows%20%7C%20macOS%20%7C%20Linux-8b5cf6)

![VideoXplainer demo: a 1-hour talk condensed to 4,000 tokens across 21 chapters, then every quote checked](https://raw.githubusercontent.com/narayan-govindaraj/videoXplainer/main/docs/demo.gif)

VideoXplainer turns a long video, or any transcript file, into a short chapter-by-chapter brief that your AI assistant can read in a fraction of the tokens. Then it checks the quotes your assistant cites against the original, so you know the summary came from the video and not from the model's imagination.

It has no LLM of its own and needs no API key. Your assistant does the reading and writing. VideoXplainer does everything around it: fetching, cleaning, condensing, and fact-checking.

## Why VideoXplainer

- **Far fewer tokens, on purpose.** Set a budget (`--budget 4000`) and get a brief that fits. A 59-minute talk went from about 17,957 tokens to 4,000: 78% less for your assistant to read.
- **Every chapter gets a share.** It uses the video's own chapters, or detects topic shifts from the text, and divides the budget across them, so the end of a video isn't crowded out by the start.
- **Receipts for every claim.** Ask your assistant for actions or points *with verbatim quotes*. `videoxplainer verify` confirms each quote is really in the video and gives you the timestamp and a deep link. Paraphrases and inventions get flagged.
- **Three views, three modes.** See raw captions, flat excerpts, or chapter-grouped passages (`--view`), and have your assistant write a summary or extract evidence-backed actions (`--mode`).
- **No API key, no extra bill.** There is nothing to configure and no second model to pay for. Use the assistant you already have.
- **One-command Claude Code setup.** `videoxplainer install-skill` installs the skill; then paste a video link. Any other agent that can run a command works too.
- **Bring your own transcripts.** Point it at a `.srt`, `.vtt`, `.json3`, `.txt` or `.md` file: meeting exports, podcast transcripts, subtitles you downloaded.
- **Private and local.** Everything you fetch lands in a local library you can search offline (`videoxplainer search "pricing advice"`). No telemetry, nothing uploaded.
- **Works across scripts.** Tested on real English, Bengali, Arabic and Bulgarian captions. Token budgets account for non-Latin text.
- **Checks itself.** `videoxplainer doctor` diagnoses your setup, and `videoxplainer check <url>` tests the whole pipeline on a real video: budget respected, every section represented, quotes verifiable.
- **Windows, macOS and Linux.** Tested in CI on all three. One `pip` install, Python 3.11 or newer.

## How it works

**1. Condense.** A real run on a public 1-hour talk (59:48):

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

About 17.9k tokens become about 4k, spread over all 21 chapters (transcript passages are elided here). No chapters on the video? VideoXplainer detects topic shifts from the text instead.

**2. Summarize.** Your assistant reads the brief and follows the task line at the bottom. In the animation above, the assistant reply and claim cards are illustrative examples.

**3. Verify.** Ask for quotes, then check them (illustrative output):

```text
$ videoxplainer verify VIDEO_ID claims.json
{ "checked": 3, "supported": 2, "weak": 0, "unsupported": 1,
  "items": [
    { "index": 0, "status": "supported",   "matched_at": "01:05", "link": "https://youtu.be/VIDEO_ID?t=65" },
    { "index": 1, "status": "supported",   "matched_at": "02:10", "link": "https://youtu.be/VIDEO_ID?t=130" },
    { "index": 2, "status": "unsupported" } ] }
```

Unsupported means the quote the assistant cited isn't in the video: drop or fix that point.

## Install

```bash
pipx install videoxplainer
videoxplainer doctor              # checks your setup (`vxp` is a short alias for the same command)
```

On Windows without `pipx`: `py -m pip install videoxplainer`, then run it as `py -m videoxplainer ...` if the command isn't on your PATH. To try the latest development version: `pipx install git+https://github.com/narayan-govindaraj/videoXplainer`.

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

**Your own transcripts.** Point `fetch` (and `verify`, `check`) at a `.srt`, `.vtt`, `.json3`, `.txt` or `.md` file. Text files with leading timestamps (`[00:12:30] ...`) keep them; files with none get timestamps estimated from word count, and the output says so. Nothing leaves your machine.

`--full` gives the complete cleaned transcript with no limit. `--refresh` re-downloads a video. `--no-chapters` ignores YouTube's chapters and detects topics from the text instead.

If YouTube asks you to prove you're not a bot: `--cookies-from-browser firefox` (Chrome/Edge cookie import is unreliable on Windows) or `--cookies-file cookies.txt`.

## Limits, honestly

- Online sources: YouTube only for now, and the video needs captions (no speech-to-text yet). Local files must already be text.
- Condensing is extractive and lossy by design. Use `--full` or `--view raw` when every word matters.
- Auto-detected sections are a heuristic. YouTube's own chapters are used whenever they exist. On two real talks with known chapters, detection from the text alone put 6 of 11 cuts within a minute of a real chapter start and recovered 7 of 25 real chapter starts; its headings are keyword lists (summary mode asks your assistant to rename them). Run `videoxplainer check <url>` to see how it does on your video.
- `verify` proves a quote exists in the video. It can't tell you the advice is good.
- Token counts are conservative estimates (about 4 characters per token for Latin text, heavier for other scripts).
- Tested on real English, Bengali, Arabic and Bulgarian captions, and on synthetic Hindi and Tamil text. Chinese, Japanese and Thai aren't word-segmented, so section detection and quote matching may be weaker there.
- YouTube changes things; if caption downloads break, update yt-dlp first (`pip install -U yt-dlp`).
- Use it for your own research and respect creators' rights and YouTube's terms.

## How it compares

| | **VideoXplainer** | [youtube-summarize](https://pypi.org/project/youtube-summarize/) (MCP) | [didntwatch](https://github.com/ewro/didntwatch) | [fabric](https://github.com/danielmiessler/fabric) | [martino-summarize](https://pypi.org/project/martino-summarize/) |
|---|---|---|---|---|---|
| Needs an LLM API key | **No** | No | No | Yes | Yes (bring your own) |
| You set a token budget | **Yes** | - | - | - | Yes (optional LLM prefilter) |
| Chapter-aware condensing | **Yes** | metadata only | - | - | - |
| Checks the AI's quotes against the video | **Yes** | - | - | - | - |
| Platforms supported | **Windows, macOS, Linux** | macOS, Windows (documented setup) | Linux, macOS | Windows, macOS, Linux | Windows, macOS, Linux |
| Sources beyond YouTube | local transcript files | - | - | articles, files, audio/video files | **11+** |
| Speech-to-text fallback | - (roadmap) | - | - | Yes (OpenAI API) | **Whisper** |

`-` means I found nothing in that project's README or code (read November 2026). Corrections welcome: please open an issue. fabric and martino-summarize call an LLM themselves; VideoXplainer hands the condensed text to the assistant you already use.

## Roadmap

- [x] v0.1 budgeted briefs, `verify`, local search
- [x] v0.2 chapter-aware condensing, three views, summary mode
- [x] v0.3 `install-skill`, local transcript files
- [ ] v0.4 `videoxplainer channel <url> --since 7d` digests, MCP server (Claude Desktop, Cursor)
- [ ] v0.5 ask your library with receipts, cross-video agreements/disagreements, optional free local speech-to-text (faster-whisper), more platforms via yt-dlp

## Credits and license

MIT. Built on [yt-dlp](https://github.com/yt-dlp/yt-dlp) (Unlicense) for caption retrieval. Developed with AI assistance (Claude).
