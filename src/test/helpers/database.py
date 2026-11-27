import sqlite3
import tempfile
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterator


_SQL_PATH = Path(__file__).parents[1] / "db" / "testgeometadb.sql"


@contextmanager
def temporary_test_database(directory: str | Path | None = None) -> Iterator[Path]:
    """Create and clean up an isolated database populated from the test SQL fixture."""
    with tempfile.TemporaryDirectory(
        prefix="geo-datasets-test-",
        dir=directory,
    ) as temporary_directory:
        database_path = Path(temporary_directory) / "testgeometadb.sqlite"
        with closing(sqlite3.connect(database_path)) as connection:
            connection.executescript(_SQL_PATH.read_text())
        yield database_path