import os
import shutil
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings

_TB = ZoneInfo("Asia/Tbilisi")
_BACKUP_AT = time(5, 0)


def backup_database(now: datetime) -> None:
    directory = settings.DB_BACKUP_DIR
    if directory == "":
        return
    local = now.astimezone(_TB)
    if local.time() < _BACKUP_AT:
        return
    destination = Path(directory) / f"db-{local.date().isoformat()}.sqlite3"
    if destination.exists():
        return
    source = Path(settings.DATABASES["default"]["NAME"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".sqlite3.tmp")
    shutil.copy2(source, temporary)
    os.replace(temporary, destination)
