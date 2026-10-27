from django.core.management.commands.migrate import Command as MigrateCommand

from tortobaza.finance_db import use_migration_db


class Command(MigrateCommand):
    def handle(self, *args, **options):
        with use_migration_db(options["database"]):
            return super().handle(*args, **options)
