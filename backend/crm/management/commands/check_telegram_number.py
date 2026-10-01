import json

from django.core.management.base import BaseCommand

from crm.telegram_user import resolve_phone


class Command(BaseCommand):
    help = "Resolve a phone number on Telegram"

    def add_arguments(self, parser):
        parser.add_argument("number")

    def handle(self, *args, **options):
        result = resolve_phone(options["number"])
        self.stdout.write(json.dumps(result, indent=2, ensure_ascii=False))
