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


DESCRIPCION_DEMO_ANTERIOR = (
    "Programa ficticio para apoyar la continuidad académica y el desarrollo profesional de estudiantes."
)
CONVOCATORIAS_DEMO = (
    (
        "Beca de continuidad universitaria", "universitario", "18000",
        "Promueve la continuidad de los estudios universitarios en Guatemala y el avance "
        "de los estudiantes en su formación académica y profesional.",
    ),
    (
        "Impulso a la educación media", "medio", "8000",
        "Busca impulsar la permanencia de los estudiantes en la educación media en Guatemala "
        "y fortalecer su preparación académica para continuar sus estudios y desarrollar sus proyectos de vida.",
    ),
    (
        "Especialización y nuevos horizontes", "posgrado", "25000",
        "Tiene como propósito fomentar la formación de posgrado y la especialización de "
        "estudiantes en Guatemala, para profundizar sus conocimientos y contribuir a su "
        "desarrollo académico y profesional.",
    ),
)


class Command(BaseCommand):
    help = "Crea cuentas y convocatorias ficticias, sin reemplazar usuarios existentes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--actualizar-textos", action="store_true",
            help="Actualiza solo descripciones antiguas reconocidas, sin crear cuentas ni convocatorias.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["actualizar_textos"]:
            actualizadas = 0
            for titulo, nivel, _, descripcion in CONVOCATORIAS_DEMO:
                # Coincidencia exacta: no modificar textos personalizados ni otros programas.
                actualizadas += Convocatoria.objects.filter(
                    titulo=titulo, nivel=nivel, descripcion=DESCRIPCION_DEMO_ANTERIOR,
                ).update(descripcion=descripcion)
            self.stdout.write(self.style.SUCCESS(
                f"Descripciones actualizadas: {actualizadas}. No se crearon datos ni se modificaron textos personalizados."
            ))
            return

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
        for titulo, nivel, monto, descripcion in CONVOCATORIAS_DEMO:
            convocatoria, _ = Convocatoria.objects.get_or_create(
                titulo=titulo,
                defaults={
                    "nivel": nivel,
                    "descripcion": descripcion,
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
