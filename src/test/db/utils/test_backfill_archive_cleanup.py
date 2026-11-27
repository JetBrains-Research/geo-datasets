import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from src.db.utils.backfill_geometadb import GEOmetadbBackfiller


class TestBackfillArchiveCleanup(unittest.TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.archive = Path(self.directory) / "GSE1.soft.gz"
        self.archive.write_bytes(b"archive")
        self.unrelated = Path(self.directory) / "other.soft.gz"
        self.unrelated.write_bytes(b"other")
        self.downloaded = SimpleNamespace(accession="GSE1", archive_path=str(self.archive))
        self.parsed = SimpleNamespace(gse=object(), gsms=[object()])
        self.downloader = SimpleNamespace(download_gse_archive=AsyncMock(return_value=self.downloaded))
        self.parser = SimpleNamespace(submit_archive_for_parsing=AsyncMock(return_value=self.parsed))
        self.backfiller = GEOmetadbBackfiller.__new__(GEOmetadbBackfiller)
        self.backfiller.gse_repository = Mock()

    def process(self):
        return asyncio.run(self.backfiller._process_single_dataset("GSE1", self.downloader, self.parser))

    def test_removes_archive_only_after_successful_save(self):
        def save(gses, gsms):
            self.assertTrue(self.archive.exists())
            self.assertEqual(gses, [self.parsed.gse])
            self.assertEqual(gsms, self.parsed.gsms)

        self.backfiller.gse_repository.save_gses_with_gsms.side_effect = save
        self.assertIs(self.process(), self.parsed.gse)
        self.assertFalse(self.archive.exists())
        self.assertTrue(self.unrelated.exists())

    def test_preserves_archive_on_parse_failure(self):
        self.parser.submit_archive_for_parsing.side_effect = ValueError("parse failed")
        with self.assertRaises(ValueError):
            self.process()
        self.assertTrue(self.archive.exists())
        self.backfiller.gse_repository.save_gses_with_gsms.assert_not_called()

    def test_preserves_archive_on_save_failure(self):
        self.backfiller.gse_repository.save_gses_with_gsms.side_effect = RuntimeError("save failed")
        with self.assertRaises(RuntimeError):
            self.process()
        self.assertTrue(self.archive.exists())

    def test_preserves_archive_when_there_are_no_samples(self):
        self.parsed.gsms = []
        self.assertIs(self.process(), self.parsed.gse)
        self.assertTrue(self.archive.exists())

    def test_cleanup_error_does_not_fail_saved_dataset(self):
        with patch.object(Path, "unlink", side_effect=PermissionError("cannot remove")):
            with self.assertLogs("src.db.utils.backfill_geometadb", level="WARNING"):
                self.assertIs(self.process(), self.parsed.gse)
        self.assertTrue(self.archive.exists())

    def test_missing_archive_does_not_fail_saved_dataset(self):
        self.archive.unlink()
        self.assertIs(self.process(), self.parsed.gse)


if __name__ == "__main__":
    unittest.main()