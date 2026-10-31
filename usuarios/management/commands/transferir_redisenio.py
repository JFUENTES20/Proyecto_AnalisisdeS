"""Importación explícita desde una copia del esquema del rediseño a una base vacía."""
import hashlib
import json
from pathlib import Path
from django.apps import apps
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.core.files import File
from django.core.files.storage import default_storage
from django.db import connections, transaction
from django.conf import settings

MODELOS = (
    "auth.group", "auth.user", "usuarios.perfil", "convocatorias.convocatoria",
    "evaluaciones.comite", "solicitudes.solicitud", "solicitudes.documento",
    "evaluaciones.evaluacion", "solicitudes.decision", "solicitudes.eventoauditoria",
    "solicitudes.notificacion", "admin.logentry",
)


def snapshot(alias):
    objetos = []
    campos = set()
    for label in MODELOS:
        model = apps.get_model(label)
        campos.update(f.name for f in model._meta.get_fields() if f.name != "fotografia")
        queryset = model._base_manager.using(alias).order_by("pk")
        if label == "usuarios.perfil":
            queryset = queryset.defer("fotografia")
        objetos.extend(queryset)
    # Este comando solo transfiere el rediseño previo, que no contenía fotografías.
    return serializers.serialize("json", objetos, fields=campos, use_natural_foreign_keys=True)



def canonico(value):
    if isinstance(value, dict):
        return {k: canonico(v) for k, v in value.items()}
    if isinstance(value, list):
        return sorted((canonico(v) for v in value), key=lambda v: json.dumps(v, sort_keys=True))
    return value


class Command(BaseCommand):
    help = "Transfiere una COPIA independiente del rediseño a una base integrada VACÍA. No modifica el origen."

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True, help="Alias Django de la copia independiente de origen")
        parser.add_argument("--database", default="default")
        parser.add_argument("--media-source", required=True)
        parser.add_argument("--confirm-source-copy", action="store_true")

    def handle(self, *args, **options):
        source, target = options["source"], options["database"]
        if not options["confirm_source_copy"]:
            raise CommandError("Confirma que --source identifica una copia independiente con --confirm-source-copy.")
        if source == target or source not in connections or target not in connections:
            raise CommandError("Se requieren dos alias distintos y configurados.")
        src, dst = connections[source], connections[target]
        def identidad(conn):
            c = conn.settings_dict
            name = str(c["NAME"])
            if conn.vendor == "sqlite":
                name = str(Path(name.split("?", 1)[0].removeprefix("file:")).resolve())
            return conn.vendor, name, c.get("HOST", ""), c.get("PORT", "")
        if identidad(src) == identidad(dst):
            raise CommandError("Origen y destino no pueden ser la misma base.")
        if "usuarios_perfil" not in src.introspection.table_names():
            raise CommandError("El origen no tiene el esquema Perfil del rediseño.")
        if "usuarios_aspirante" in src.introspection.table_names():
            raise CommandError("El origen debe ser una copia del rediseño previo, no una base ya reconciliada.")
        if "usuarios_aspirante" not in dst.introspection.table_names():
            raise CommandError("Migra primero el esquema integrado del destino.")
        modelos = [apps.get_model(label) for label in MODELOS]
        if any(model._base_manager.using(target).exists() for model in modelos) or apps.get_model("usuarios.Aspirante").objects.using(target).exists():
            raise CommandError("El destino debe estar vacío de usuarios y datos de negocio.")
        root = Path(options["media_source"]).resolve()
        if root == Path(settings.MEDIA_ROOT).resolve():
            raise CommandError("El almacenamiento destino debe ser independiente del origen.")
        payload = snapshot(source)
        documentos = apps.get_model("solicitudes.Documento").objects.using(source).all()
        archivos = {}
        for doc in documentos:
            name = doc.archivo.name
            path = (root / name).resolve()
            if not name or Path(name).is_absolute() or not path.is_relative_to(root) or not path.is_file():
                raise CommandError("Documento ausente o ruta fuera de la copia: " + str(doc.pk))
            if default_storage.exists(name):
                raise CommandError("El destino ya contiene un archivo con la misma ruta.")
            archivos[name] = path
        creados = []
        try:
            with transaction.atomic(using=target):
                pendientes = []
                for obj in serializers.deserialize("json", payload, using=target, handle_forward_references=True):
                    obj.save(using=target)
                    if obj.deferred_fields:
                        pendientes.append(obj)
                for obj in pendientes:
                    obj.save_deferred_fields(using=target)
                for name, path in archivos.items():
                    with path.open("rb") as stream:
                        guardado = default_storage.save(name, File(stream))
                    creados.append(guardado)
                    if guardado != name:
                        raise CommandError("El almacenamiento cambió la referencia de un documento.")
                    with default_storage.open(name, "rb") as stream:
                        if hashlib.file_digest(stream, "sha256").digest() != hashlib.sha256(path.read_bytes()).digest():
                            raise CommandError("El contenido del documento no coincide.")
                if canonico(json.loads(snapshot(target))) != canonico(json.loads(payload)):
                    raise CommandError("La verificación de cuentas, contraseñas o relaciones no coincide.")
                with dst.cursor() as cursor:
                    for sql in dst.ops.sequence_reset_sql(no_style(), modelos):
                        cursor.execute(sql)
        except Exception:
            for name in creados:
                default_storage.delete(name)
            raise
        self.stdout.write(self.style.SUCCESS(
            f"Transferencia verificada: {len(json.loads(payload))} registros y {len(archivos)} archivos. Origen intacto."
        ))
