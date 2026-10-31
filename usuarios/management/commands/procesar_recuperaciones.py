import time
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from usuarios.models import LimiteRecuperacion, SolicitudRecuperacion
from usuarios.recuperacion import procesar_uno


class Command(BaseCommand):
    help = "Procesa la cola de recuperación; usa exclusivamente el backend EMAIL_BACKEND configurado."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument("--watch", action="store_true")
        parser.add_argument("--interval", type=float, default=2)
        parser.add_argument("--limpiar", action="store_true")

    def handle(self, *args, **options):
        if options["limit"] < 1 or options["interval"] < 0.2:
            from django.core.management.base import CommandError
            raise CommandError("Usa limit positivo e interval de al menos 0.2 segundos.")
        if options["limpiar"]:
            LimiteRecuperacion.objects.filter(ventana__lt=timezone.now()-timedelta(days=1)).delete()
            SolicitudRecuperacion.objects.exclude(estado="pendiente").filter(creada__lt=timezone.now()-timedelta(days=7)).delete()
        try:
            while True:
                cantidad = 0
                while cantidad < options["limit"] and procesar_uno():
                    cantidad += 1
                if not options["watch"]:
                    self.stdout.write(f"Solicitudes procesadas: {cantidad}. Esto no confirma entrega a una bandeja.")
                    return
                time.sleep(options["interval"])
        except KeyboardInterrupt:
            return
