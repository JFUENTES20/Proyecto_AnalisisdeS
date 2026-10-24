"""Perfil.telefono es el contacto vigente; Aspirante.telefono es archivo histórico."""
import re
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from .models import Perfil, Aspirante, EventoContacto
from .permisos import rol_de

SALT = "guatebecas.perfil-contacto"


def normalizar_telefono(valor):
    compacto = valor.strip().replace(" ", "").replace("\u00a0", "")
    match = re.fullmatch(r"(?:\+502)?([2-7][0-9]{7})", compacto)
    if not match:
        raise ValidationError("Ingresa un teléfono guatemalteco de 8 dígitos que comience entre 2 y 7; puedes usar espacios o +502.")
    return "+502" + match.group(1)


def telefono_historico(usuario):
    return Aspirante.objects.filter(user_id=usuario.pk).values_list("telefono", flat=True).first() or ""


def hay_discrepancia(actual, historico):
    def comparable(valor):
        try:
            return normalizar_telefono(valor)
        except ValidationError:
            return valor.strip()
    return bool(historico.strip()) and comparable(actual) != comparable(historico)


def version_contacto(perfil):
    return signing.dumps({"perfil": perfil.pk, "telefono": perfil.telefono}, salt=SALT)


@transaction.atomic
def actualizar_telefono(actor, telefono, version, confirmar=False):
    if rol_de(actor) != "aspirante":
        raise PermissionDenied
    perfil = Perfil.objects.select_for_update().get(usuario_id=actor.pk)
    if perfil.rol != "aspirante":
        raise PermissionDenied
    try:
        previo = signing.loads(version, salt=SALT, max_age=3600)
    except signing.BadSignature:
        raise ValidationError("El formulario expiró o no es válido. Recarga Mi perfil antes de guardar.")
    if previo != {"perfil": perfil.pk, "telefono": perfil.telefono}:
        raise ValidationError("El teléfono cambió desde que abriste esta página. Recarga Mi perfil y revisa el valor actual.")
    if hay_discrepancia(perfil.telefono, telefono_historico(actor)) and not confirmar:
        raise ValidationError("Confirma el teléfono de contacto después de revisar la diferencia con el dato histórico.")
    nuevo = normalizar_telefono(telefono)
    if nuevo == perfil.telefono:
        return False
    anterior = perfil.telefono
    perfil.telefono = nuevo
    perfil.save(update_fields=["telefono"])
    EventoContacto.objects.create(perfil=perfil, responsable=actor, telefono_anterior=anterior, telefono_nuevo=nuevo)
    return True
