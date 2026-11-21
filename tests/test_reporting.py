import io
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from pypodcastde import cli
from pypodcastde.config import Podcast


class ReportingTests(unittest.TestCase):
    def test_preview_reports_mixed_outcomes(self):
        shows = [Podcast(name, Path("."), "", None) for name in ("First", "Second", "Third")]
        stream = io.StringIO()
        with (
            redirect_stderr(stream),
            patch.object(cli, "load", return_value=shows),
            patch.object(cli, "crawl", side_effect=[OSError("offline"), 1, 0]),
        ):
            self.assertEqual(cli.main(["mine", "--force", "--try"]), 1)
        last = stream.getvalue().splitlines()[-1]
        self.assertIn("Summary (force preview) | shows succeeded: 1 | failed: 2", last)
        self.assertIn("First, Second", last)

    def test_config_error_and_interruption_still_report(self):
        for error, status, detail in [
            (ValueError("bad table"), 1, "configuration error"),
            (KeyboardInterrupt(), 130, "interrupted"),
        ]:
            stream = io.StringIO()
            with redirect_stderr(stream), patch.object(cli, "load", side_effect=error):
                self.assertEqual(cli.main(["mine"]), status)
            last = stream.getvalue().splitlines()[-1]
            self.assertIn("Summary (update)", last)
            self.assertIn(detail, last)
