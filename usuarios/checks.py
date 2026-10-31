import ipaddress
from urllib.parse import urlsplit
from django.conf import settings
from django.core.checks import Error, register


@register()
def configuracion_recuperacion(app_configs, **kwargs):
    errores = []
    if settings.EMAIL_USE_TLS and settings.EMAIL_USE_SSL:
        errores.append(Error("EMAIL_USE_TLS y EMAIL_USE_SSL no pueden activarse juntos.", id="usuarios.E001"))
    if min(settings.PASSWORD_RESET_TIMEOUT, settings.PASSWORD_RESET_RATE_WINDOW,
           settings.PASSWORD_RESET_EMAIL_LIMIT, settings.PASSWORD_RESET_IP_LIMIT, settings.EMAIL_TIMEOUT) <= 0:
        errores.append(Error("Timeouts y límites de recuperación deben ser positivos.", id="usuarios.E002"))
    try:
        for red in settings.PASSWORD_RESET_TRUSTED_PROXIES:
            ipaddress.ip_network(red)
    except ValueError:
        errores.append(Error("Proxy de recuperación inválido; usa IP o red explícita.", id="usuarios.E003"))
    if settings.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend" and not settings.EMAIL_HOST:
        errores.append(Error("Configura EMAIL_HOST para utilizar SMTP.", id="usuarios.E006"))
    origen = settings.PASSWORD_RESET_PUBLIC_ORIGIN
    try:
        p = urlsplit(origen)
        valido = p.scheme in {"http", "https"} and bool(p.hostname) and not p.username and not p.password and p.path in {"", "/"} and not p.query and not p.fragment
        if not settings.DEBUG:
            valido = valido and p.scheme == "https"
    except ValueError:
        valido = False
    if origen and not valido:
        errores.append(Error("Configura un origen canónico válido en PASSWORD_RESET_PUBLIC_ORIGIN (HTTPS fuera de DEBUG).", id="usuarios.E004"))
    return errores


@register(deploy=True)
def origen_produccion(app_configs, **kwargs):
    if not settings.DEBUG and not settings.PASSWORD_RESET_PUBLIC_ORIGIN:
        return [Error("Configura PASSWORD_RESET_PUBLIC_ORIGIN antes de servir recuperación en producción.", id="usuarios.E005")]
    if (not settings.DEBUG and settings.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend"
            and not (settings.EMAIL_USE_TLS or settings.EMAIL_USE_SSL)):
        return [Error("Usa STARTTLS o SSL para SMTP público.", id="usuarios.E007")]
    return []
