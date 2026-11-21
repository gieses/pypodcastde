"""Configure crawler logs and report the outcome of each crawl cycle."""

import http.client
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from loguru import logger
from yt_dlp.utils import DownloadError


def configure_logging() -> None:
    """Route CLI logs to stderr with a timestamp and the current show's name."""
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <7}</level> | "
            "<cyan>{extra[show]}</cyan> | <level>{message}</level>"
        ),
        backtrace=False,
        diagnose=False,
    )
    logger.configure(extra={"show": "crawler"})


@dataclass
class RunSummary:
    """Track completed shows and configuration errors for one run."""

    succeeded: int = 0
    failed: list[str] = field(default_factory=list)
    config_error: bool = False

    def crawl(self, name: str, action: Callable[[], int]) -> None:
        """Record an action's exit status or recoverable exception under the show name."""
        with logger.contextualize(show=name):
            try:
                status = action()
            except (
                DownloadError,
                OSError,
                RuntimeError,
                ValueError,
                KeyError,
                http.client.HTTPException,
            ) as exc:
                logger.error("Crawl failed: {}", exc)
                status = 1
            if status:
                self.failed.append(name)
            else:
                self.succeeded += 1

    @property
    def status(self) -> int:
        """Return a nonzero CLI status if configuration or any show failed."""
        return int(bool(self.failed) or self.config_error)


@contextmanager
def report_run(dry_run: bool, force: bool) -> Iterator[RunSummary]:
    """Yield a fresh tally and log its summary even if the run is interrupted."""
    summary = RunSummary()
    mode = ("force" if force else "update") + (" preview" if dry_run else "")
    finished = False
    try:
        yield summary
        finished = True
    finally:
        reason = []
        if not finished:
            reason.append("run interrupted or aborted")
        if summary.config_error:
            reason.append("configuration error")
        if summary.failed:
            reason.append("failed: " + ", ".join(summary.failed))
        logger.log(
            "ERROR" if reason else "SUCCESS",
            "Summary ({}) | shows succeeded: {} | failed: {}{}",
            mode,
            summary.succeeded,
            len(summary.failed),
            " | " + "; ".join(reason) if reason else "",
        )
