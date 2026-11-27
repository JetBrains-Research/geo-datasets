import datetime
import os
import tempfile
from pathlib import Path


def update_geometadb(geometadb_path, backfill, end_date=None):
    marker = Path(geometadb_path).parent / "geo_backfill_last_success.txt"
    try:
        last_success = marker.read_text().strip()
    except FileNotFoundError:
        last_success = ""

    start_date = (datetime.date.fromisoformat(last_success) - datetime.timedelta(days=2)
                  if last_success else datetime.date(2024, 3, 6))
    end_date = end_date or datetime.date.today()
    backfill(datetime.datetime.combine(start_date, datetime.time.min),
             datetime.datetime.combine(end_date, datetime.time.min))

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=marker.parent, prefix=f".{marker.name}.",
                                         delete=False) as temporary_file:
            temporary_path = temporary_file.name
            temporary_file.write(f"{end_date.isoformat()}\n")
        os.replace(temporary_path, marker)
    finally:
        if temporary_path is not None and os.path.exists(temporary_path):
            os.unlink(temporary_path)