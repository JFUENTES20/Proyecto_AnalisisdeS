"""Procesamiento de imágenes y operaciones limitadas al aspirante autenticado."""
import logging
import warnings
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.db import transaction

from .models import EventoFotografia, Perfil
from .permisos import rol_de

MAX_BYTES = 2 * 1024 * 1024
MAX_PIXELES = 12_000_000
MAX_LADO = 6000


def preparar_fotografia(archivo):
    if archivo.size > MAX_BYTES:
        raise ValidationError("La fotografía debe pesar como máximo 2 MB.")
    datos = archivo.read(MAX_BYTES + 1)
    if len(datos) > MAX_BYTES:
        raise ValidationError("La fotografía debe pesar como máximo 2 MB.")
    extension = Path(archivo.name).suffix.lower()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(datos)) as imagen:
                if imagen.format not in {"JPEG", "PNG"} or extension not in {".jpg", ".jpeg", ".png"}:
                    raise ValidationError("Selecciona una fotografía JPG o PNG válida.")
                ancho, alto = imagen.size
                if max(ancho, alto) > MAX_LADO or ancho * alto > MAX_PIXELES:
                    raise ValidationError("La imagen supera el límite de 12 megapíxeles o 6000 píxeles por lado. Reduce sus dimensiones en un editor de imágenes hasta cumplir ambos límites y vuelve a seleccionarla.")
                if getattr(imagen, "n_frames", 1) != 1:
                    raise ValidationError("Utiliza una imagen estática, sin animación.")
                imagen.verify()
            with Image.open(BytesIO(datos)) as imagen:
                imagen.load()
                orientada = ImageOps.exif_transpose(imagen)
                cuadrada = ImageOps.fit(orientada, (512, 512), method=Image.Resampling.LANCZOS)
                # Un lienzo nuevo elimina EXIF y otros metadatos; transparencia sobre blanco.
                limpia = Image.new("RGB", cuadrada.size, "white")
                rgba = cuadrada.convert("RGBA")
                limpia.paste(rgba, mask=rgba.getchannel("A"))
                salida = BytesIO()
                limpia.save(salida, "JPEG", quality=85, optimize=True)
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
            Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError("El archivo no es una imagen JPG o PNG válida o está dañado.")
    return ContentFile(salida.getvalue(), name=f"{uuid4().hex}.jpg")


def _eliminar_archivo(storage, nombre):
    try:
        storage.delete(nombre)
    except OSError:
        logging.getLogger(__name__).exception("No se pudo limpiar una fotografía retirada.")


def cambiar_fotografia(actor, archivo=None, eliminar=False):
    if not actor.is_authenticated or rol_de(actor) != "aspirante":
        raise PermissionDenied
    contenido = None if eliminar else preparar_fotografia(archivo)
    nuevo = None
    storage = Perfil._meta.get_field("fotografia").storage
    try:
        with transaction.atomic():
            perfil = Perfil.objects.select_for_update().get(usuario_id=actor.pk)
            if perfil.rol != "aspirante":
                raise PermissionDenied
            anterior = perfil.fotografia.name
            if eliminar and not anterior:
                return False
            if not eliminar:
                nuevo = storage.save("perfiles/" + contenido.name, contenido)
            perfil.fotografia = nuevo or ""
            perfil.save(update_fields=["fotografia"])
            EventoFotografia.objects.create(perfil=perfil, responsable=actor,
                operacion="eliminar" if eliminar else ("reemplazar" if anterior else "subir"))
            if anterior:
                transaction.on_commit(lambda: _eliminar_archivo(storage, anterior))
    except Exception:
        if nuevo:
            _eliminar_archivo(storage, nuevo)
        raise
    return True
