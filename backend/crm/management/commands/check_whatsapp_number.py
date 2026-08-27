import json

from django.core.management.base import BaseCommand

from crm.whatsapp import check_number


class Command(BaseCommand):
    help = "Check whether a phone number is registered on WhatsApp"

    def add_arguments(self, parser):
        parser.add_argument("number")

    def handle(self, *args, **options):
        result = check_number(options["number"])
        self.stdout.write(json.dumps(result, indent=2, ensure_ascii=False))
