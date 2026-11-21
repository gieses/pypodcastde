"""Extract MP3s from video sources using yt-dlp and FFmpeg."""

import shutil
from pathlib import Path

from loguru import logger
from yt_dlp import YoutubeDL


class VideoLogger:
    """Adapt yt-dlp's logging callbacks to the crawler's per-show logger."""

    @staticmethod
    def debug(message: str) -> None:
        """Forward normal status lines while suppressing yt-dlp debug diagnostics."""
        # yt-dlp also sends its ordinary informational messages to debug().
        if not message.startswith("[debug]"):
            logger.info(message)

    warning = staticmethod(logger.warning)
    error = staticmethod(logger.error)


class LoggedYoutubeDL(YoutubeDL):
    """Keep yt-dlp preview titles in the crawl log."""

    def to_stdout(self, message: str, *args: object, **kwargs: object) -> None:
        """Log preview titles that would otherwise bypass the configured logger."""
        logger.info(message)


def mine(url: str, out: Path, dry_run: bool, *, force: bool = False) -> int:
    """Preview or extract audio from a video or playlist and return yt-dlp's status."""
    if not dry_run and not all(shutil.which(tool) for tool in ("ffmpeg", "ffprobe")):
        raise RuntimeError("Video conversion requires ffmpeg and ffprobe on PATH")
    # The archive records past downloads, not MP3s still on disk. The ID in
    # each filename survives title changes and lets update repair deleted files.
    saved = (
        {
            path.stem.rsplit(" [", 1)[-1]
            for path in out.glob("*.mp3")
            if path.stem.endswith("]") and path.is_file() and path.stat().st_size
        }
        if not force
        else set()
    )

    def skip_saved(info: dict[str, object], *, incomplete: bool | set[str]) -> str | None:
        """Return a yt-dlp skip reason when the video's ID has a nonempty MP3."""
        if info.get("id") and info.get("_type", "video") == "video":
            suffix = downloader.prepare_filename(info, outtmpl="x [%(id)s].mp3")
            if Path(suffix).stem.removeprefix("x [") in saved:
                return f"Already downloaded: {info.get('title') or info['id']}"
        return None

    options = {
        "logger": VideoLogger(),
        "noprogress": True,
        "paths": {"home": str(out)},
        "outtmpl": {"default": "%(title).130s [%(id)s].%(ext)s"},
        "windowsfilenames": True,
        "format": "bestaudio/best",
        "match_filter": skip_saved if not force else None,
        "overwrites": True,
        "continuedl": False,
        "cachedir": False,
        "simulate": dry_run,
        "ignoreerrors": True,  # Continue a playlist; download() returns nonzero on failure.
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
    }
    if dry_run:
        options["forceprint"] = {"video": ["Would download: %(title)s"]}
    with LoggedYoutubeDL(options) as downloader:
        return downloader.download([url])
