from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Send a test email through the configured SMTP server"

    def add_arguments(self, parser):
        parser.add_argument("email")

    def handle(self, *args, **options):
        recipient = options["email"]
        send_mail(
            "SMTP test",
            "Test email from Gmail SMTP",
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
        )
        self.stdout.write(f"Sent to {recipient}")
