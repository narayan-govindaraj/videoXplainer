# Contributing

Small, focused PRs are welcome.

```bash
git clone https://github.com/narayan-govindaraj/videoxplainer && cd videoxplainer
python -m pip install -e ".[dev]"
python -m pytest -q
```

- Tests must not touch the network (see `tests/test_fetch_cli.py` for the fake yt-dlp pattern).
- Keep dependencies at zero beyond yt-dlp; that is a feature.
- Bug reports: include the output of `videoxplainer doctor` and the exact command. For caption-download failures, say whether you used cookies.
