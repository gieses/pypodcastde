"""Download the shows in a locations file, once or every 24 hours."""

import argparse
import csv
import os
import time
from pathlib import Path

from loguru import logger

from . import checkpod, nico, video
from .config import Podcast, default_config, example_config, load
from .modes import add_mode_options
from .reporting import configure_logging, report_run

DAY = 24 * 60 * 60


def crawl(podcast: Podcast, dry_run: bool, force: bool) -> int:
    """Run the downloader appropriate for the source and return its exit status."""
    logger.info("Destination: {}", podcast.destination)
    if podcast.show_id == nico.SHOW_ID:
        return nico.mine(podcast.destination, dry_run, force=force)
    if podcast.show_id:
        prefix = checkpod.SHOW_PREFIX if podcast.show_id == checkpod.SHOW_ID else podcast.name
        return checkpod.mine(podcast.show_id, prefix, podcast.destination, dry_run, force=force)
    return video.mine(podcast.url, podcast.destination, dry_run, force=force)


def update(path: Path, root: Path | None, dry_run: bool, force: bool = False) -> int:
    """Read the show list and continue with the next show if a download fails."""
    with report_run(dry_run, force) as summary:
        try:
            podcasts = load(path, root)
        except (OSError, ValueError, csv.Error) as exc:
            logger.error("Cannot load {}: {}", path, exc)
            if isinstance(exc, FileNotFoundError):
                logger.info(
                    "Create a private table with 'pypodcastde init-config' or pass --config PATH"
                )
            summary.config_error = True
        else:
            for podcast in podcasts:
                summary.crawl(podcast.name, lambda p=podcast: crawl(p, dry_run, force))
    return summary.status


def main(argv: list[str] | None = None) -> int:
    """Run the requested CLI command; return 130 if a crawl or wait is interrupted."""
    parser = argparse.ArgumentParser(description="Update local podcast directories")
    parser.add_argument(
        "command",
        choices=["mine", "schedule", "init-config"],
        help="update once, schedule daily, or create a private locations table",
    )
    parser.add_argument(
        "--config", type=Path, default=default_config(), help="semicolon-separated locations table"
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=os.getenv("PYPODCASTDE_OUTPUT_ROOT"),
        help="place each destination directory under this root",
    )
    add_mode_options(parser)
    args = parser.parse_args(argv)
    configure_logging()
    if args.command == "init-config":
        try:
            template = example_config().read_bytes()
            with args.config.open("xb") as stream:
                stream.write(template)
        except OSError as exc:
            logger.error("Cannot create {}: {}", args.config, exc)
            return 1
        logger.success("Created {}. Edit the locations before crawling.", args.config)
        return 0
    try:
        while True:
            start = time.monotonic()
            status = update(args.config, args.output_root, args.dry_run, args.force)
            if args.command == "mine":
                return status
            logger.info("Next crawl scheduled 24 hours from the start of this run")
            time.sleep(max(0, DAY - (time.monotonic() - start)))
    except KeyboardInterrupt:
        return 130
