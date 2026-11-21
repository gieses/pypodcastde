# Changelog

## [0.1.0](https://github.com/gieses/pypodcastde/releases/tag/v0.1.0) - 2026-11-21

First release.

- Download ARD audio shows and save video soundtracks as MP3s. The example locations file includes eight German children's shows.
- Run `pypodcastde mine` to download missing episodes or `pypodcastde schedule` to check every 24 hours. Add `--try` to preview a run or `--force` to replace existing downloads.
- Keep folder paths in a private locations file. Use local folders, Windows shares, or a mounted share on Linux.
- Run on a server with Docker Compose. The image includes FFmpeg and ffprobe. Each crawl logs which shows succeeded and which failed.
