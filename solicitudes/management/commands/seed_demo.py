import os
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from convocatorias.models import Convocatoria
from evaluaciones.models import Comite
from usuarios.models import Perfil


class Command(BaseCommand):
    help = "Crea cuentas y convocatorias ficticias, sin reemplazar usuarios existentes."

    @transaction.atomic
    def handle(self, *args, **options):
        clave = os.environ.get("DEMO_PASSWORD")
        if not clave or len(clave) < 12:
            raise CommandError(
                "Define DEMO_PASSWORD con al menos 12 caracteres. Solo para desarrollo."
            )
        cuentas = [
            ("administrador.demo", "Demo", "Administración", "administrador"),
            ("aspirante.demo", "Ana", "López", "aspirante"),
            ("evaluador.demo", "Carlos", "Pérez", "evaluador"),
            ("aprobador.uno", "Elena", "García", "aprobador"),
            ("aprobador.dos", "Luis", "Morales", "aprobador"),
        ]
        for username, nombre, apellido, rol in cuentas:
            usuario, creado = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": nombre,
                    "last_name": apellido,
                    "email": username + "@example.com",
                },
            )
            if creado:
                if rol == "administrador":
                    usuario.is_staff = True
                    usuario.is_superuser = True
                usuario.set_password(clave)
                usuario.save()
                Perfil.objects.create(usuario=usuario, rol=rol)
            self.stdout.write(
                f"{username}: " + ("creada" if creado else "existente, sin cambios")
            )
        hoy = timezone.localdate()
        for titulo, nivel, monto in [
            ("Beca de continuidad universitaria", "universitario", "18000"),
            ("Impulso a la educación media", "medio", "8000"),
            ("Especialización y nuevos horizontes", "posgrado", "25000"),
        ]:
            convocatoria, _ = Convocatoria.objects.get_or_create(
                titulo=titulo,
                defaults={
                    "nivel": nivel,
                    "descripcion": "Programa ficticio para apoyar la continuidad académica y el desarrollo profesional de estudiantes.",
                    "requisitos": "Constancia de estudios.\nCertificación de notas.\nCarta de motivación.",
                    "monto_maximo": Decimal(monto),
                    "apertura": hoy - timedelta(days=3),
                    "cierre": hoy + timedelta(days=45),
                    "publicada": True,
                },
            )
            comite, _ = Comite.objects.get_or_create(
                nombre="Comité · " + titulo, convocatoria=convocatoria
            )
            comite.miembros.add(User.objects.get(username="evaluador.demo"))
        self.stdout.write(
            self.style.SUCCESS(
                "Datos ficticios listos. La contraseña proviene de DEMO_PASSWORD."
            )
        )
