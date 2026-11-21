import io
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from loguru import logger

from pypodcastde import checkpod, nico, video


class ModeTests(unittest.TestCase):
    def test_audio_downloads_match_preview(self):
        episodes = [
            {
                "id": title,
                "title": title,
                "publishDate": "2026-01-01",
                "duration": 1,
                "audios": [{"url": f"https://example.org/{title}.mp3"}],
            }
            for title in ("Saved", "Empty", "Missing")
        ]
        for backend in (checkpod, nico):
            for force in (False, True):
                with (
                    self.subTest(backend=backend.__name__, force=force),
                    tempfile.TemporaryDirectory() as tmp,
                ):
                    out = Path(tmp)
                    prefix = backend.SHOW_PREFIX
                    args = (backend.SHOW_ID, prefix, out) if backend is checkpod else (out,)
                    saved, empty, missing = [
                        out / f"{prefix} - 2026-01-01 - {ep['title']}.mp3" for ep in episodes
                    ]
                    saved.write_bytes(b"original")
                    empty.touch()
                    manifest = out / "episodes.json"
                    manifest.write_text("untouched")
                    expected = {empty, missing} | ({saved} if force else set())
                    output = io.StringIO()
                    with (
                        patch.object(backend, "fetch_episodes", return_value=episodes),
                        patch.object(
                            backend,
                            "download",
                            side_effect=lambda _, path: path.write_bytes(b"new"),
                        ) as dl,
                        ExitStack() as stack,
                    ):
                        stack.callback(logger.remove, logger.add(output, format="{message}"))
                        self.assertEqual(backend.mine(*args, dry_run=True, force=force), 0)
                        dl.assert_not_called()
                        self.assertEqual(manifest.read_text(), "untouched")
                        self.assertFalse(missing.exists())
                        for path in (saved, empty, missing):
                            self.assertEqual(path.stem in output.getvalue(), path in expected)
                        self.assertEqual(backend.mine(*args, dry_run=False, force=force), 0)
                        self.assertEqual({call.args[1] for call in dl.call_args_list}, expected)
                        self.assertEqual(saved.read_bytes(), b"new" if force else b"original")

    def test_video_selection_uses_mp3s_not_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "Old title [saved].mp3").write_bytes(b"original")
            (out / "Empty [empty].mp3").touch()
            archive = out / ".video-archive"
            archive.write_text("generic missing\n")
            for dry_run in (False, True):
                for force in (False, True):

                    def inspect_options(downloader, urls, dry_run=dry_run, force=force):
                        self.assertEqual(downloader.params["simulate"], dry_run)
                        self.assertFalse(downloader.params.get("download_archive"))
                        self.assertTrue(downloader.params["overwrites"])
                        decide = downloader.params["match_filter"]
                        for ident in ("saved", "empty", "missing"):
                            skipped = decide and decide(
                                {"title": "New title", "id": ident}, incomplete=False
                            )
                            self.assertEqual(bool(skipped), ident == "saved" and not force)
                        return 0

                    with (
                        self.subTest(dry_run=dry_run, force=force),
                        patch.object(video.YoutubeDL, "download", inspect_options),
                        patch.object(video.shutil, "which", return_value="installed"),
                    ):
                        self.assertEqual(
                            video.mine("https://example.org/video", out, dry_run, force=force), 0
                        )
            self.assertEqual(archive.read_text(), "generic missing\n")
