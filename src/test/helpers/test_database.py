import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from src.test.helpers.database import temporary_test_database


class TestTemporaryDatabase(unittest.TestCase):
    def test_databases_are_seeded_isolated_and_cleaned_up(self) -> None:
        """Verify fixture contents, per-test isolation, and cleanup."""
        with (
            temporary_test_database() as first_database,
            temporary_test_database() as second_database,
        ):
            self.assertNotEqual(first_database, second_database)
            with closing(sqlite3.connect(first_database)) as connection:
                self.assertGreater(connection.execute("SELECT COUNT(*) FROM gse").fetchone()[0], 0)
                connection.execute("INSERT INTO gse (gse) VALUES (?)", ("GSE_TEST_ISOLATION",))
                connection.commit()

            with closing(sqlite3.connect(second_database)) as connection:
                self.assertEqual(
                    0,
                    connection.execute(
                        "SELECT COUNT(*) FROM gse WHERE gse = ?",
                        ("GSE_TEST_ISOLATION",),
                    ).fetchone()[0],
                )

        self.assertFalse(first_database.exists())
        self.assertFalse(second_database.exists())

    def test_database_can_be_created_in_requested_directory(self) -> None:
        """Verify fixture databases can share a caller-selected filesystem."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            with temporary_test_database(temporary_directory) as database_path:
                self.assertEqual(Path(temporary_directory), database_path.parent.parent)
                self.assertTrue(database_path.is_file())