import os
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Displays the GOOGLE_APPLICATION_CREDENTIALS environment variable'

    def handle(self, *args, **kwargs):
        creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if creds:
            self.stdout.write(self.style.SUCCESS(f'GOOGLE_APPLICATION_CREDENTIALS: {creds}'))
        else:
            self.stdout.write(self.style.ERROR('GOOGLE_APPLICATION_CREDENTIALS environment variable not set'))
