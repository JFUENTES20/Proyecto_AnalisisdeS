"""Recuperación Django, límite compartido y outbox sin tokens persistidos."""
import ipaddress
import logging
from datetime import timedelta
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.views import PasswordResetConfirmView, PasswordResetView
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives
from django.db import DatabaseError, connection, transaction
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from .models import LimiteRecuperacion, SolicitudRecuperacion

logger = logging.getLogger(__name__)


def huella(scope, valor):
    return salted_hmac("recuperacion." + scope, valor, algorithm="sha256").hexdigest()


def correo_normalizado(valor):
    return valor.strip().casefold()


class RecuperacionForm(PasswordResetForm):
    enviados = 0

    def get_users(self, email):
        # Incluye inactivos y claves inutilizables al detectar ambigüedad.
        if get_user_model().objects.filter(email__iexact=email).count() != 1:
            return iter(())
        return super().get_users(email)

    def send_mail(self, subject_template_name, email_template_name, context,
                  from_email, to_email, html_email_template_name=None):
        subject = "".join(render_to_string(subject_template_name, context).splitlines())
        body = render_to_string(email_template_name, context)
        mensaje = EmailMultiAlternatives(subject, body, from_email, [to_email])
        if mensaje.send(fail_silently=False) != 1:
            raise OSError("El backend no aceptó el mensaje")
        self.enviados += 1


def ip_cliente(request):
    remoto = request.META.get("REMOTE_ADDR", "")
    try:
        address = ipaddress.ip_address(remoto)
    except ValueError:
        return "desconocida"
    confiable = any(address in ipaddress.ip_network(red) for red in settings.PASSWORD_RESET_TRUSTED_PROXIES)
    if confiable:
        # Nginx debe REEMPLAZAR el encabezado con $remote_addr, no concatenarlo.
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").strip()
        try:
            return str(ipaddress.ip_address(forwarded))
        except ValueError:
            pass
    return str(address)


@transaction.atomic
def permitido(request, email):
    now = timezone.now()
    aceptado = True
    for scope, valor, maximo in (("ip", ip_cliente(request), settings.PASSWORD_RESET_IP_LIMIT),
                                 ("correo", correo_normalizado(email), settings.PASSWORD_RESET_EMAIL_LIMIT)):
        limite, _ = LimiteRecuperacion.objects.get_or_create(
            clave=huella(scope, valor), defaults={"ventana": now})
        limite = LimiteRecuperacion.objects.select_for_update().get(pk=limite.pk)
        if now - limite.ventana >= timedelta(seconds=settings.PASSWORD_RESET_RATE_WINDOW):
            limite.ventana, limite.intentos = now, 0
        # Saturar el contador evita overflow ante abuso persistente.
        limite.intentos = min(limite.intentos + 1, maximo + 1)
        limite.save(update_fields=["ventana", "intentos"])
        aceptado = aceptado and limite.intentos <= maximo
    return aceptado


def origen_correo(request):
    origen = settings.PASSWORD_RESET_PUBLIC_ORIGIN
    if not origen:
        if not settings.DEBUG:
            raise ImproperlyConfigured("Configura PASSWORD_RESET_PUBLIC_ORIGIN antes de habilitar recuperación pública.")
        origen = request.scheme + "://" + request.get_host()
    parts = urlsplit(origen)
    if (parts.scheme not in {"http", "https"} or not parts.netloc or parts.username
            or parts.password or parts.path not in {"", "/"} or parts.query or parts.fragment
            or (not settings.DEBUG and parts.scheme != "https")):
        raise ImproperlyConfigured("PASSWORD_RESET_PUBLIC_ORIGIN debe ser un origen HTTP local o HTTPS público, sin ruta ni credenciales.")
    return origen.rstrip("/")


class SolicitarRecuperacionView(PasswordResetView):
    template_name = "registration/password_reset_form.html"
    form_class = RecuperacionForm

    def form_valid(self, form):
        origen = origen_correo(self.request)
        try:
            if permitido(self.request, form.cleaned_data["email"]):
                usuarios = list(form.get_users(form.cleaned_data["email"]))
                usuario = usuarios[0] if len(usuarios) == 1 else None
                # También se encola la solicitud desconocida/ambigua: respuesta uniforme.
                SolicitudRecuperacion.objects.create(usuario=usuario, origen=origen,
                    correo_hash=huella("correo", correo_normalizado(form.cleaned_data["email"])),
                    password_hash=huella("password", usuario.password) if usuario else "")
        except DatabaseError:
            logger.error("recuperacion_solicitud_no_persistida")
        return HttpResponseRedirect(self.get_success_url())


def procesar_uno():
    with transaction.atomic():
        queryset = SolicitudRecuperacion.objects.filter(estado="pendiente").order_by("pk")
        if connection.features.has_select_for_update_skip_locked:
            queryset = queryset.select_for_update(skip_locked=True)
        else:
            queryset = queryset.select_for_update()
        solicitud = queryset.first()
        if solicitud is None:
            return False
        solicitud.estado = "procesando"
        solicitud.save(update_fields=["estado"])
    estado = "omitido"
    try:
        usuario = get_user_model().objects.filter(pk=solicitud.usuario_id).first()
        if (usuario and usuario.is_active and usuario.has_usable_password()
                and timezone.now() - solicitud.creada < timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT)
                and constant_time_compare(solicitud.correo_hash, huella("correo", correo_normalizado(usuario.email)))
                and constant_time_compare(solicitud.password_hash, huella("password", usuario.password))):
            form = RecuperacionForm({"email": usuario.email})
            if form.is_valid() and [u.pk for u in form.get_users(usuario.email)] == [usuario.pk]:
                parts = urlsplit(solicitud.origen)
                form.save(domain_override=parts.netloc, use_https=parts.scheme == "https",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    subject_template_name="registration/password_reset_subject.txt",
                    email_template_name="registration/password_reset_email.txt")
                estado = "aceptado" if form.enviados == 1 else "omitido"
    except Exception:
        # No registrar dirección, token, credenciales ni excepción del proveedor.
        estado = "fallido"
        logger.error("recuperacion_envio_fallido")
    SolicitudRecuperacion.objects.filter(pk=solicitud.pk).update(estado=estado, procesada=timezone.now())
    return True


class ConfirmarRecuperacionView(PasswordResetConfirmView):
    def get_user(self, uidb64):
        usuario = super().get_user(uidb64)
        if usuario is None or not usuario.is_active or not usuario.has_usable_password():
            return None
        if get_user_model().objects.filter(email__iexact=usuario.email).count() != 1:
            return None
        return usuario
