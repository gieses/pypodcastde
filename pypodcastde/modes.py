"""Shared command-line options for download selection and previews."""

from argparse import ArgumentParser


def add_mode_options(parser: ArgumentParser) -> None:
    """Register mutually exclusive update/force flags and an independent preview flag."""
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--update",
        dest="force",
        action="store_false",
        help="download missing or empty episodes only (default)",
    )
    modes.add_argument(
        "--force",
        action="store_true",
        help="download every available episode, including existing ones",
    )
    parser.set_defaults(force=False)
    parser.add_argument(
        "--try",
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="preview the selected mode without changing the library",
    )
