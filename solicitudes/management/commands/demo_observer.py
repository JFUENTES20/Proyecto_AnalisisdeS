from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "El ejemplo anterior se reemplazó por un flujo real y auditable."

    def handle(self, *args, **options):
        raise CommandError("Usa seed_demo y la interfaz web; ver README.md.")
