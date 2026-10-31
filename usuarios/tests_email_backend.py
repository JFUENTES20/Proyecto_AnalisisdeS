import ssl
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.core import mail
from django.core.management import call_command
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from .checks import configuracion_recuperacion, origen_produccion
from .models import SolicitudRecuperacion
from .recuperacion import procesar_uno


@override_settings(EMAIL_BACKEND="usuarios.email_backend.EmailBackend", EMAIL_CA_BUNDLE="",
    EMAIL_HOST="smtp.example.test", EMAIL_PORT=587, EMAIL_USE_TLS=True, EMAIL_USE_SSL=False,
    EMAIL_HOST_USER="usuario-test", EMAIL_HOST_PASSWORD="valor-sintetico-no-real",
    PASSWORD_RESET_PUBLIC_ORIGIN="https://becas.example.test")
class BackendCorreoTests(TestCase):
    def test_contexto_predeterminado_verifica_certificado_y_hostname(self):
        c = mail.get_connection().ssl_context
        self.assertEqual(c.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(c.check_hostname)

    def test_cafile_explicito_se_aplica_sin_desactivar_validacion(self):
        with override_settings(EMAIL_CA_BUNDLE="/ruta-sintetica/ca.pem"), patch("usuarios.email_backend.ssl.create_default_context", return_value=ssl.create_default_context()) as factory:
            c = mail.get_connection().ssl_context
            factory.assert_called_once_with(cafile="/ruta-sintetica/ca.pem")
            self.assertTrue(c.check_hostname)
            self.assertEqual(c.verify_mode, ssl.CERT_REQUIRED)

    def test_ca_inexistente_falla_cerrada(self):
        with override_settings(EMAIL_CA_BUNDLE="/no-existe-guatebecas/ca.pem"):
            with self.assertRaises(OSError):mail.get_connection().ssl_context
            self.assertIn("usuarios.E008", {e.id for e in configuracion_recuperacion(None)})

    def test_ca_invalida_rechazada(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"ca.pem";p.write_text("no es un certificado")
            with override_settings(EMAIL_CA_BUNDLE=str(p)):
                with self.assertRaises(ssl.SSLError):mail.get_connection().ssl_context

    def test_transporte_starttls_usa_contexto_publicado(self):
        with patch("django.core.mail.backends.smtp.smtplib.SMTP") as smtp:
            smtp.return_value.sendmail.return_value={}
            self.assertEqual(mail.send_mail("Prueba", "Mensaje sintético", "no-responder@example.test", ["destino@example.test"]), 1)
            context=smtp.return_value.starttls.call_args.kwargs["context"]
            self.assertTrue(context.check_hostname)
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            smtp.return_value.login.assert_called_once_with("usuario-test","valor-sintetico-no-real")

    def test_trabajador_con_backend_publicado_y_origen_https(self):
        u=User.objects.create_user("tls-prueba","tls@example.test","ClaveSoloPrueba2026!")
        original=u.password
        self.client.post("/recuperar/",{"email":u.email})
        with patch("django.core.mail.backends.smtp.smtplib.SMTP") as smtp:
            smtp.return_value.sendmail.return_value={}
            self.assertTrue(procesar_uno())
            self.assertIn(b"https://becas.example.test/recuperar/",smtp.return_value.sendmail.call_args.args[2])
            self.assertEqual(smtp.return_value.starttls.call_args.kwargs["context"].verify_mode,ssl.CERT_REQUIRED)
        self.assertEqual(SolicitudRecuperacion.objects.get().estado,"aceptado")
        u.refresh_from_db();self.assertEqual(u.password,original)

    @override_settings(DEBUG=False,ROOT_URLCONF="becas_platform.urls")
    def test_produccion_sin_buzones_y_archivos_privados(self):
        for url in ("/demo-correo/","/.local/correos/","/correos/"):
            self.assertEqual(self.client.get(url,secure=True).status_code,404)
        self.assertEqual(origen_produccion(None),[])

    @override_settings(DEBUG=False,EMAIL_BACKEND="django.core.mail.backends.filebased.EmailBackend",ROOT_URLCONF="recuperacion_urls")
    def test_deploy_rechaza_backend_y_urlconf_privados(self):
        self.assertEqual({e.id for e in origen_produccion(None)},{"usuarios.E009","usuarios.E010"})
