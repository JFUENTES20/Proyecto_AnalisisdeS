import json
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from solicitudes.models import Solicitud


class Command(BaseCommand):
    help = "Lista expedientes sin propietario y candidatos por correo; NO asigna ni modifica datos."

    def handle(self, *args, **options):
        pendientes = []
        for solicitud in Solicitud.objects.filter(aspirante__isnull=True).order_by("pk"):
            email = solicitud.email.strip()
            candidatos = list(get_user_model().objects.filter(email__iexact=email).order_by("pk").values_list("pk", flat=True)) if email else []
            pendientes.append({"solicitud": solicitud.pk, "candidatos": candidatos,
                               "revision": "ambigua" if len(candidatos) > 1 else "manual"})
        self.stdout.write(json.dumps(pendientes))
