# Roadmap issues (paste into GitHub)

For each one: Issues, then New issue, paste the title and body, set the labels and milestone shown. All labels used are GitHub defaults. Create the two milestones first (Issues, then Milestones, then New milestone): `v0.4` and `v0.5`.

Suggested order of work, by reach and impact against effort: 1 (MCP) first, then 2, 3, 4. Issue 5 is the "help wanted" one.

---

## 1. MCP server so Claude Desktop, Cursor and other MCP clients can use VideoXplainer

**Labels:** enhancement  **Milestone:** v0.4

**Why**
Today VideoXplainer needs an agent that can run a command. Chat apps such as Claude Desktop can't, so a large group of potential users can't use it yet.

**Proposal**
- `videoxplainer mcp` starts an MCP server over stdio, installed as an optional extra: `pip install "videoxplainer[mcp]"`.
- Tools: `fetch_brief` (url or file path, budget, view, mode, lang), `verify_claims` (video, claims), `search_library` (query), `check_video` (url).
- Tool outputs match the CLI text.
- Setup docs for Claude Desktop and Cursor (config file paths for Windows and macOS).

**Acceptance criteria**
- Works in Claude Desktop on Windows and macOS.
- Automated tests against a stub MCP client.
- README section with copy-paste config.
- `videoxplainer doctor` reports whether the MCP extra is installed.
- Default budget keeps tool responses well under client output limits (some clients cap tool output at roughly 25k tokens), so keep the default at or below 8,000.

**Out of scope:** a hosted or remote server.

---

## 2. Channel and playlist digests: `videoxplainer channel <url> --since 7d`

**Labels:** enhancement  **Milestone:** v0.4

**Why**
People follow channels, not single videos. A weekly digest saves the most time.

**Proposal**
- Enumerate a channel's or playlist's uploads via yt-dlp (flat listing), keep only videos since a date or since the last run.
- Condense each video within a total budget shared across the digest.
- Remember "last run" locally so reruns fetch only new videos.
- Options: `--max N`, `--budget`, `--mode summary`.

**Acceptance criteria**
- The total budget is respected across the whole digest.
- Reruns skip videos already in the library.
- Works for a channel URL and a playlist URL.
- Tests with a fake yt-dlp, with no network.
- Clear errors for rate limiting and for videos without captions.

**Notes:** large channels need sensible caps and polite pacing.

---

## 3. Ask your library, with receipts

**Labels:** enhancement  **Milestone:** v0.5

**Why**
The local library already searches videos by keyword. The natural next step is to answer a question from everything you've watched, with the sources attached.

**Proposal**
- Passage-level index in SQLite FTS5 (each cached transcript split into timestamped passages).
- `videoxplainer ask "question" --budget 3000` returns the best passages across videos, each with video title, timestamp and deep link, followed by a task line for the assistant.
- Then `verify` can check the assistant's quotes, as today.
- No embeddings in v1, to keep the install small.

**Acceptance criteria**
- Hand-label about 20 queries over a small test library and report recall@5 in the PR.
- Output stays within the budget.
- Works offline.

---

## 4. Optional local speech-to-text (faster-whisper) for videos without captions and for local audio/video files

**Labels:** enhancement, help wanted  **Milestone:** v0.5

**Why**
Videos without captions currently fail, and many recordings (meetings, lectures) exist only as audio or video.

**Proposal**
- Optional extra: `pip install "videoxplainer[asr]"` (faster-whisper, MIT licensed).
- `--asr auto|off|force`. Download audio with yt-dlp for online videos, or read local files directly.
- CPU int8 by default, selectable model size, progress output, and cached transcripts.
- Document the one-time model download and expected speed on CPU.

**Acceptance criteria**
- A 10-minute sample transcribes on CPU, with the speed documented.
- `verify` works on ASR transcripts.
- Works on Windows, macOS and Linux.
- Docs explain the accuracy trade-offs between model sizes.

**Out of scope:** speaker labels.

---

## 5. Improve topic detection and section headings (benchmark first)

**Labels:** enhancement, help wanted, good first issue  **Milestone:** v0.5

**Why**
For videos without chapters, sections come from a heuristic. Measured against real YouTube chapters on two English talks: 6 of 11 detected cuts landed within 60 seconds of a real chapter start, and 7 of 25 real chapter starts were recovered. Headings are keyword lists.

**Proposal**
1. Build a small benchmark: a script that, for videos with known chapters, reports how many auto-detected cuts fall near real chapter starts and how many real starts are recovered. Store only timestamps and chapter titles, never transcripts.
2. Then try improvements (better keyword labels, adaptive section count, smoothing) and report the numbers.

**Acceptance criteria**
- A reproducible benchmark script, runnable with `videoxplainer check` data.
- Any change must not lower precision below the current baseline (6 of 11).
- The PR reports before and after numbers.
- No new runtime dependencies if possible.

**Good first step:** just the benchmark script (item 1).

---

## Optional: a GitHub Discussion

Create a Discussion titled "Which platform should come next?" (Vimeo, X, TikTok, podcasts...) and link it from the README roadmap. It's a cheap, honest way to let demand pick the next extractor.
