# Launch posts (drafts)

Every number below was measured in this project's own runs. Don't add claims you haven't measured. Before posting anywhere, re-read that community's rules and use your own words where you can.

---

## Show HN

**Title (pick one, max 80 characters):**
1. `Show HN: VideoXplainer – Shrink video transcripts for LLMs and verify quotes`
2. `Show HN: VideoXplainer – Condense a video to N tokens, verify the AI's quotes`

**URL:** https://github.com/narayan-govindaraj/videoXplainer

(Hacker News takes a URL *or* text, not both, so put everything else in your first comment.)

**First comment (post it yourself right after submitting):**

> Author here. I kept pasting full YouTube transcripts into Claude. A one-hour talk is about 18k tokens, and the summaries sometimes contained points the speaker never made. VideoXplainer is a small Python CLI (MIT, no API key, no LLM inside) that sits between the video and your assistant.
>
> How it works: it fetches captions with yt-dlp, cleans them (sound tags, fillers, the repeated lines in auto-captions), splits the video into chapters (YouTube's own, or detected from shifts in vocabulary between neighbouring passages), then keeps the highest-scoring passages in each chapter under a token budget you set. Your assistant gets that brief plus a task line (summary, or actions with verbatim quotes). A second command, `verify`, checks every quote the assistant cites against the transcript (exact match first, then fuzzy windows) and gives you the timestamp and a deep link, or flags it as not in the video.
>
> Numbers from real runs: a 59:48 talk went from ~17,957 to ~4,000 tokens across its 21 chapters; a 20-minute talk from ~5,174 to ~1,990 at a 2,000 budget. On the four real videos I tested, 5/5 real quotes verified and 0/5 scrambled quotes slipped through. Those are single examples, not averages.
>
> Limits: YouTube only for now, and the video needs captions. The condensing is extractive, so it's lossy (there's `--full` and a raw view). When a video has no chapters, topic detection from the text is a heuristic: on two talks with known chapters it put 6 of 11 cuts within a minute of a real chapter start and recovered 7 of 25 real chapters. `verify` proves a quote exists, not that the advice is good.
>
> I built it with Claude's help; there are 90 automated tests and CI on Windows, macOS and Linux. Install: `pipx install videoxplainer`. I'd love to hear about videos where it fails (`videoxplainer check <url>` prints a report you can paste into an issue), whether the condensing drops things that matter to you, and what you'd want next. An MCP server is my next candidate.

**Posting tips:** Tuesday to Thursday, 8–10am US Eastern (about 6:30–8:30pm in India). Don't ask for upvotes. Stay online and reply for 3–4 hours. Answer criticism with specifics, not defensiveness.

---

## Reddit: r/ClaudeAI

**Title:** `I built a CLI that shrinks YouTube transcripts to a token budget (and checks Claude's quotes against the video)`

> I kept pasting whole YouTube transcripts into Claude. A one-hour talk is ~18k tokens, and I couldn't tell which points in the summary the speaker actually made.
>
> So I built VideoXplainer, a small open-source CLI (MIT, no API key, no LLM of its own). It condenses a video chapter by chapter to a token budget you choose (my 59-minute test talk went from ~17,957 to ~4,000 tokens across 21 chapters). Then, when Claude cites quotes, `verify` checks each one against the transcript and gives you the timestamp, or tells you it isn't in the video.
>
> It also works on transcript files (.srt, .vtt, .txt) like meeting exports and podcasts, and installs a Claude Code skill with one command (`videoxplainer install-skill`).
>
> Honest limits: YouTube only for now, needs captions, the condensing is lossy (a raw/full mode exists), and topic detection for videos without chapters is a heuristic. Built with Claude's help.
>
> Repo + demo: https://github.com/narayan-govindaraj/videoXplainer. I'd really like to hear which videos break it and what you'd want next (MCP server is on my list).

*Attach the GIF or MP4 to the post directly rather than linking it. Check whether the subreddit requires a flair and whether it limits self-promotion.*

---

## Reddit: r/ClaudeCode (post a day later, shorter, workflow-focused)

**Title:** `A Claude Code skill that reads a YouTube video in ~4k tokens instead of ~18k, with quote checking`

> `pipx install videoxplainer`, then `videoxplainer install-skill`, restart Claude Code, and paste a YouTube link. The skill runs `videoxplainer fetch` with a token budget, Claude summarises chapter by chapter from the condensed text, and `videoxplainer verify` checks its quotes against the transcript. No API key, no extra model.
>
> On a 59-minute talk: ~17,957 to ~4,000 tokens, all 21 chapters represented. Works on .srt/.vtt/.txt too. MIT, built with Claude's help. https://github.com/narayan-govindaraj/videoXplainer
>
> Feedback welcome, especially videos that fail: `videoxplainer check <url>` gives a report you can paste into an issue.

---

## Canned replies for common questions

**"Why not just let the LLM summarize the whole transcript?"**
For a 5-minute video, do exactly that. For an hour-long talk the full transcript is ~18k tokens, which costs context and money, and nothing checks the summary against the source. This keeps the structure and shrinks the input, then verifies the quotes.

**"How is this different from NotebookLM and similar tools?"**
I haven't compared against closed products, so I won't claim to. This is a local, open-source tool that works with whichever assistant you already use, with no keys, and its distinct part is the token budget plus quote verification. The README compares it against the open-source tools I could read.

**"Does it work with ChatGPT or Gemini?"**
Any agent that can run a command can use it directly. For a plain chat window, copy the output instead: on Windows `videoxplainer fetch <url> --mode summary --budget 4000 | clip`, on macOS use `pbcopy` instead of `clip`, then paste it into the chat.

**"YouTube blocks me / asks me to sign in."**
Try `--cookies-from-browser firefox` (Chrome and Edge cookie import is unreliable on Windows) or `--cookies-file cookies.txt`, and update yt-dlp (`pip install -U yt-dlp`). `videoxplainer doctor` flags an outdated yt-dlp.

**"Is this okay with YouTube's terms?"**
It uses yt-dlp to read publicly available captions for your own research. Respect creators' rights and YouTube's terms. I'm not a lawyer, and it's your responsibility how you use it.

**"Why extractive condensing instead of an LLM?"**
It's deterministic, free, offline and explainable, and it needs no key. The cost is that it's lossy, which is why `--full` and the raw view exist. An optional LLM-assisted mode could be a future add-on if people want it.
