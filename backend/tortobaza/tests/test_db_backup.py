from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase

from tortobaza.db_backup import backup_database

_TB = ZoneInfo("Asia/Tbilisi")


class BackupDatabaseTests(SimpleTestCase):
    def test_before_five_does_not_copy(self):
        with TemporaryDirectory() as source_dir, TemporaryDirectory() as backup_dir:
            source = Path(source_dir) / "db.sqlite3"
            source.write_bytes(b"sqlite")
            self._backup(source, backup_dir, datetime(2026, 10, 26, 4, 59, tzinfo=_TB))
            self.assertEqual(list(Path(backup_dir).iterdir()), [])

    def test_at_five_copies_database(self):
        with TemporaryDirectory() as source_dir, TemporaryDirectory() as backup_dir:
            source = Path(source_dir) / "db.sqlite3"
            source.write_bytes(b"sqlite")
            self._backup(source, backup_dir, datetime(2026, 10, 26, 5, 0, tzinfo=_TB))
            destination = Path(backup_dir) / "db-2026-10-26.sqlite3"
            self.assertEqual(destination.read_bytes(), b"sqlite")
            self.assertFalse(destination.with_suffix(".sqlite3.tmp").exists())

    def test_second_call_same_day_does_not_overwrite(self):
        with TemporaryDirectory() as source_dir, TemporaryDirectory() as backup_dir:
            source = Path(source_dir) / "db.sqlite3"
            source.write_bytes(b"sqlite")
            self._backup(source, backup_dir, datetime(2026, 10, 26, 5, 0, tzinfo=_TB))
            destination = Path(backup_dir) / "db-2026-10-26.sqlite3"
            destination.write_bytes(b"kept")
            source.write_bytes(b"changed")
            self._backup(source, backup_dir, datetime(2026, 10, 26, 12, 0, tzinfo=_TB))
            self.assertEqual(destination.read_bytes(), b"kept")

    def test_empty_backup_dir_does_nothing(self):
        with TemporaryDirectory() as source_dir:
            source = Path(source_dir) / "db.sqlite3"
            source.write_bytes(b"sqlite")
            self._backup(source, "", datetime(2026, 10, 26, 5, 0, tzinfo=_TB))
            self.assertEqual(source.read_bytes(), b"sqlite")

    def _backup(self, source: Path, backup_dir: str, now: datetime) -> None:
        with patch("tortobaza.db_backup.settings") as mock_settings:
            mock_settings.DB_BACKUP_DIR = backup_dir
            mock_settings.DATABASES = {"default": {"NAME": source}}
            backup_database(now)
