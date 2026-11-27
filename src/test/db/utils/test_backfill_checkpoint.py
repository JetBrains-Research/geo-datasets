import asyncio
import datetime
import runpy
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.db.utils.backfill_checkpoint import update_geometadb


class TestBackfillCheckpoint(unittest.TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.database = Path(self.directory) / "custom.sqlite"
        self.marker = Path(self.directory) / "geo_backfill_last_success.txt"
        self.end_date = datetime.date(2025, 2, 5)
        self.backfill = Mock()

    def update(self):
        update_geometadb(str(self.database), self.backfill, self.end_date)

    def test_initial_update_and_resume_use_database_directory(self):
        self.update()
        self.backfill.assert_called_once_with(datetime.datetime(2024, 3, 6), datetime.datetime(2025, 2, 5))
        self.assertEqual("2025-02-05\n", self.marker.read_text())

        self.backfill.reset_mock()
        self.end_date = datetime.date(2025, 2, 6)
        self.update()
        self.backfill.assert_called_once_with(datetime.datetime(2025, 2, 3), datetime.datetime(2025, 2, 6))
        self.assertEqual("2025-02-06\n", self.marker.read_text())

    def test_empty_marker_uses_initial_date(self):
        self.marker.write_text("\n")
        self.update()
        self.assertEqual(datetime.datetime(2024, 3, 6), self.backfill.call_args.args[0])

    def test_failure_does_not_advance_marker(self):
        self.marker.write_text("2025-01-03\n")
        self.backfill.side_effect = RuntimeError("failed")
        with self.assertRaises(RuntimeError):
            self.update()
        self.assertEqual("2025-01-03\n", self.marker.read_text())

    def test_invalid_marker_fails_before_backfill(self):
        self.marker.write_text("invalid\n")
        with self.assertRaises(ValueError):
            self.update()
        self.backfill.assert_not_called()
        self.assertEqual("invalid\n", self.marker.read_text())

    def test_failed_replace_preserves_marker_and_cleans_temporary_file(self):
        self.marker.write_text("2025-01-03\n")
        with patch("src.db.utils.backfill_checkpoint.os.replace", side_effect=OSError("failed")):
            with self.assertRaises(OSError):
                self.update()
        self.assertEqual("2025-01-03\n", self.marker.read_text())
        self.assertEqual([self.marker], list(Path(self.directory).iterdir()))


class TestBackfillCommand(unittest.TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.marker = Path(self.directory) / "geo_backfill_last_success.txt"
        config = Mock(geometadb_path=str(Path(self.directory) / "database.sqlite"))
        self.accessions = Mock(return_value=[])
        self.modules = {}
        for name, attributes in {
            "aiohttp": {},
            "sqlalchemy": {},
            "sqlalchemy.exc": {"SQLAlchemyError": Exception, "DBAPIError": Exception},
            "tqdm": {},
            "tqdm.asyncio": {"tqdm_asyncio": Mock()},
            "src.config.config": {"Config": Mock(return_value=config)},
            "src.config.configure_log_file": {"configure_log_file": Mock()},
            "src.db.models": {"GSE": object},
            "src.db.repositories.gse_repository": {"GSERepository": Mock()},
            "src.db.repositories.gsm_repository": {"GSMRepository": Mock()},
            "src.db.utils.get_geo_accessions_for_dates": {"get_gse_ids_by_last_update_date": self.accessions},
            "src.db.utils.gse_archive_downloader": {"GSEArchiveDownloader": Mock()},
            "src.db.utils.gse_archive_parser": {"GSEArchiveParser": Mock()},
            "src.exception.disk_space_error": {"DiskSpaceError": Exception},
        }.items():
            module = types.ModuleType(name)
            module.__dict__.update(attributes)
            self.modules[name] = module

    @staticmethod
    def close_coroutine(coroutine, **kwargs):
        coroutine.close()
        return []

    def run_command(self, *args):
        with patch.dict(sys.modules, self.modules), patch.object(sys, "argv", ["backfill", *args]), \
                patch.object(asyncio, "run", side_effect=self.close_coroutine):
            runpy.run_module("src.db.utils.backfill_geometadb", run_name="__main__")

    def test_update_command_uses_checkpoint_and_advances_it(self):
        self.marker.write_text("2025-01-03\n")
        self.run_command("--update")
        self.assertEqual(datetime.datetime(2025, 1, 1), self.accessions.call_args.args[0])
        self.assertEqual(datetime.date.today().isoformat(), self.marker.read_text().strip())

    def test_explicit_dates_do_not_modify_checkpoint(self):
        self.marker.write_text("2025-01-03\n")
        self.run_command("2024-01-01", "2024-02-01")
        self.accessions.assert_called_once_with(datetime.datetime(2024, 1, 1), datetime.datetime(2024, 2, 1))
        self.assertEqual("2025-01-03\n", self.marker.read_text())

    def test_update_command_failure_does_not_advance_checkpoint(self):
        self.marker.write_text("2025-01-03\n")
        self.accessions.side_effect = RuntimeError("failed")
        with self.assertRaises(RuntimeError):
            self.run_command("--update")
        self.assertEqual("2025-01-03\n", self.marker.read_text())

    def test_update_rejects_dates_and_ignored_failures(self):
        for args in (("--update", "2024-01-01"), ("--update", "--ignore-failures"), ()):
            with self.subTest(args=args), self.assertRaises(SystemExit) as error:
                self.run_command(*args)
            self.assertEqual(2, error.exception.code)
        self.assertFalse(self.marker.exists())
        self.accessions.assert_not_called()