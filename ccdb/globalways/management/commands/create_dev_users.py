from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

USERS = (("testing", "LjERtTXIOkBG996h", "ccdb-testing@dc1.com"),)


class Command(BaseCommand):
    help = "create dev users for development and testing"

    def handle(self, *args, **options):
        for user, password, email in USERS:
            u, c = User.objects.get_or_create(
                username=user,
                defaults={
                    "is_superuser": True,
                    "is_staff": True,
                    "first_name": user,
                    "last_name": "Tester",
                    "email": email,
                },
            )
            u.set_password(password)
            u.save()
