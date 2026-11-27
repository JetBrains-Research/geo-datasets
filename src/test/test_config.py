import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config.config import Config


class TestConfig(unittest.TestCase):
    def test_test_mode_accepts_isolated_database_without_test_path_setting(self) -> None:
        """Verify test mode uses an explicit database path without a test config property."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            config_path = temporary_path / "config.properties"
            config_path.write_text(
                "geometadb_path = /production/geometadb.sqlite\n"
                "max_ncbi_connections = 10\n"
                "small_dataset_parser_workers = 1\n"
                "big_dataset_parser_workers = 1\n"
                "big_gzip_threshold_mb = 65\n"
                f"dataset_download_folder = {temporary_path / 'downloads'}\n"
                "show_backfill_progress = true\n"
                "embeddings_service_url = http://localhost:5001\n"
                "max_tokens_per_chunk = 64\n"
                "overlap_sentences = 1\n"
                "chunking_workers = 1\n"
                "archive_parser_chunk_size = 1\n"
                "embeddings_batch_size = 1\n"
            )
            database_path = temporary_path / "testgeometadb.sqlite"

            with patch.object(Config, "CONFIG_PATHS", []):
                default_config = Config(test=True, path=str(config_path))
                config = Config(test=True, path=str(config_path), geometadb_path=str(database_path))

            self.assertEqual("/production/geometadb.sqlite", default_config.geometadb_path)
            self.assertEqual(str(database_path), config.geometadb_path)