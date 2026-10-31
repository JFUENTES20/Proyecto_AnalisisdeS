"""SMTP publicable con CA configurable, sin desactivar verificación TLS."""
import ssl
from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend as DjangoSMTPBackend
from django.utils.functional import cached_property


class EmailBackend(DjangoSMTPBackend):
    @cached_property
    def ssl_context(self):
        # Una ruta inválida falla cerrada; nunca se reintenta sin verificar.
        context = ssl.create_default_context(cafile=settings.EMAIL_CA_BUNDLE or None)
        if self.ssl_certfile:
            context.load_cert_chain(self.ssl_certfile, self.ssl_keyfile)
        return context
