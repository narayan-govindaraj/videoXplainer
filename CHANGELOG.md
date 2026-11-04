# Changelog

## 0.3.3
- Requires Python 3.11 or newer. Current yt-dlp needs 3.11+, and older Pythons would be stuck on a frozen, outdated yt-dlp that YouTube changes will break.
- README: corrected the language-support note (real vs synthetic test data).

## 0.3.2
- Cleaner auto-detected section headings (no contractions or conversational filler).
- `check` prints full error messages (including the list of available caption languages).

## 0.3.1
- New: `fetch --no-chapters` ignores YouTube's chapters and detects topics from the text.
- `check` also benchmarks topic auto-detection against a video's real chapters (information only).

## 0.3.0
- New: `videoxplainer install-skill` installs the Claude Code skill in one command (`--dir`, `--force`, `--print`).
- New: local transcript files (`.srt .vtt .json3 .txt .md`) work with `fetch`, `verify` and `check`; plain text without timestamps gets estimated ones.
- New: `vxp` is a short alias for the `videoxplainer` command.
- `--lang` is now strict: you never silently get another language or a machine translation; the error lists what is available. The library re-fetches when you ask for a different language than the one stored.
- Library upgrades itself automatically (new column), no action needed.
- Topic auto-detection only cuts at significant shifts, so long topics aren't split in pieces and a uniform talk stays whole.

## 0.2.2
- Fix: section detection, passage ranking and `verify` only understood Latin letters, so Hindi/Tamil/other non-Latin captions were handled poorly. Now Unicode-aware.
- Token estimates are conservative for non-Latin scripts, so budgets aren't overshot.
- New: `videoxplainer check <url>...` self-tests the pipeline on real videos.
- `videoxplainer doctor` warns when yt-dlp is more than 90 days old.
- CI also builds the package and smoke-tests the installed command.

## 0.2.1
- Fix: condensed briefs no longer include meaningless fragments; a section with nothing worth quoting is dropped instead of padded.

## 0.2.0
- Chapter-aware condensing: every YouTube chapter (or auto-detected topic) gets a share of the token budget.
- Views: `--view chapters|excerpts|raw`. Modes: `--mode text|summary|actions`.
- Library now stores chapter markers (older libraries upgrade automatically; use `--refresh` once per video).

## 0.1.1
- Fix: tiny fragments selected on small budgets; timeline coverage kept on small budgets.

## 0.1.0
- First release: token-budgeted briefs, `verify` (quote check), local full-text search, Windows/macOS/Linux CI.
