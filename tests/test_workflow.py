import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pypodcastde import cli
from pypodcastde.config import default_config, example_config, load


class WorkflowTests(unittest.TestCase):
    def test_bundled_locations_can_be_rebased(self):
        root = Path("portable")
        shows = load(example_config(), root)
        self.assertEqual(
            {p.name for p in shows},
            {
                "Checker Tobi",
                "Checkerin Marina",
                "Alle Gegen Nico",
                "Lachlabor",
                "Anna und die wilden Tiere",
                "Die Maus zum Hören",
                "Kakadu",
                "Ohrenbär",
            },
        )
        self.assertEqual({p.destination.parent for p in shows}, {root})
        self.assertEqual(len({p.show_id for p in shows}), 8)

    def test_init_config_never_overwrites_private_table(self):
        self.assertEqual(default_config(), Path.cwd() / "locations_local.txt")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "locations_local.txt"
            args = ["init-config", "--config", str(path)]
            self.assertEqual(cli.main(args), 0)
            self.assertEqual(path.read_bytes(), example_config().read_bytes())
            self.assertTrue(
                all(p.destination.parent == path.parent / "podcasts" for p in load(path, None))
            )
            path.write_text("private")
            self.assertEqual(cli.main(args), 1)
            self.assertEqual(path.read_text(), "private")

    def test_custom_table_with_quoted_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "custom.txt"
            path.write_text(
                'Podcast Name;Location;URL\n"My; Show";media;https://example.com/movie.mp4\n'
            )
            with patch.object(cli.video, "mine", return_value=0) as mine:
                self.assertEqual(cli.main(["mine", "--config", str(path), "--dry-run"]), 0)
                mine.assert_called_once_with(
                    "https://example.com/movie.mp4", path.parent / "media", True, force=False
                )
            self.assertFalse((path.parent / "media").exists())

    def test_schedule_retries_after_failed_run(self):
        with (
            patch.object(cli, "update", side_effect=[1, 0]) as update,
            patch.object(cli.time, "monotonic", side_effect=[0, 30, 86400, 86460]),
            patch.object(cli.time, "sleep", side_effect=[None, KeyboardInterrupt]) as sleep,
        ):
            self.assertEqual(cli.main(["schedule"]), 130)
            self.assertEqual(update.call_count, 2)
            self.assertEqual([c.args[0] for c in sleep.call_args_list], [86370, 86340])
