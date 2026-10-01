from django.core.management.base import BaseCommand

from crm.telegram_user import login_user


class Command(BaseCommand):
    help = "Log in a Telegram user account and print the session string"

    def handle(self, *args, **options):
        self.stdout.write(login_user())
