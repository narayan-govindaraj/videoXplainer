# Security

videoxplainer runs locally. It sends no telemetry and has no server. Network access is yt-dlp talking to YouTube.

- Browser cookies are read only if you pass `--cookies-from-browser` / `--cookies-file`, and are handed to yt-dlp, never stored by videoxplainer.
- Fetched captions are cached in a local SQLite file (`videoxplainer doctor` prints the path).

Report vulnerabilities privately via GitHub "Report a vulnerability" on this repository's Security tab.
