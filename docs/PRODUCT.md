# VideoXplainer: product notes

**In one line:** condense a long video to a token budget, chapter by chapter, and check the quotes an AI cites against the source.

## The problem

Learning from long videos with an AI assistant fails in two ways. First, cost and context: a one-hour talk is about 18,000 tokens. Second, trust: the summary can contain points the speaker never made, and nothing checks it. Existing tools mostly either paste the whole transcript or call their own LLM (which needs an API key). Neither addresses trust.

## Who it's for

People who already use an AI assistant (Claude Code, other agents, or a chat window via copy and paste) to learn from videos, meetings and podcasts, and want fewer tokens and checkable output. Primary users are developers and power users; researchers and students are a likely second group.

## What it does

- **Condenses** a transcript to a token budget you set, giving every chapter a share.
- **Verifies** the quotes an assistant cites against the original, with timestamps and deep links.
- **Stays local**: no API key, no model of its own, no telemetry.

## Key decisions and trade-offs

| Decision | Why | Cost |
|---|---|---|
| No LLM inside; the assistant does the reading | No key, no extra bill, private, works with any agent | Can't write summaries standalone |
| Extractive condensing (passage scoring per chapter), not LLM compression | Deterministic, free, offline, explainable | Lossy, so `--full` and a raw view exist |
| Budget split across chapters | The end of a video isn't crowded out by the start | Needs chapters; the fallback is a heuristic |
| Quote verification as the core differentiator | Turns "trust me" into receipts | Proves a quote exists, not that advice is good |
| Python 3.11+ | Current yt-dlp requires it; older Pythons would be stuck on a frozen downloader | Excludes 3.9 and 3.10 users |
| YouTube first, other platforms later | A competitor already covers many platforms; extractors are high-maintenance | Narrower reach for now |

## Evidence

- **Token reduction (single examples, not averages):** 17,957 to 4,000 tokens on a 59:48 talk; 5,174 to 1,990 on a 20-minute talk at a 2,000 budget.
- **Quote check round-trip:** on all four real videos tested, 5 of 5 real quotes were supported and 0 of 5 scrambled quotes were accepted.
- **Languages:** real captions in English (uploaded and auto), Bengali, Arabic and Bulgarian; Hindi and Tamil tested on synthetic text only.
- **Engineering:** 90 automated tests, CI on Windows, macOS and Linux across Python 3.11, 3.12 and 3.14, published to PyPI through trusted publishing.
- **Topic detection against real chapters:** 6 of 11 detected cuts landed within a minute of a real chapter start; 7 of 25 real chapter starts were recovered.

## What real data changed

- The ranking and quote-matching code only understood Latin letters. Testing with non-Latin scripts exposed it; it is now Unicode-aware and checked on real Bengali, Arabic and Bulgarian captions.
- Reading four competitors' code corrected my own comparison table: one of them already had speech-to-text.
- Using YouTube's own chapters as ground truth put numbers on topic detection instead of impressions.
- `--lang` once silently returned a different language; it is now strict and lists what is available.
- The dependency analysis showed the downloader needs Python 3.11+, after a CI failure on 3.9, so I raised the minimum.

## Risks

- YouTube and yt-dlp change often; bot checks affect some networks.
- Only a handful of real videos tested so far; real-world accuracy beyond that is unknown.
- Competitors could add token budgets. The defensible parts are verification and execution.
- Adoption is unknown.

## Roadmap and prioritization

Ordered by reach and impact against effort:

1. **MCP server**: unlocks Claude Desktop and Cursor, the biggest group who can't use it today.
2. **Channel digests**: follows channels, not single videos.
3. **Ask your library with receipts**: builds on the local library and verification.
4. **Local speech-to-text**: covers videos without captions and local recordings.
5. **Better topic detection**: benchmark first, help wanted.

See the open issues for details.

## How it was built

Scoped in phases, with tests alongside each feature and real-video validation before any claim went into the README. Developed with AI assistance (Claude), with me setting scope, reviewing and running the real-world tests.
