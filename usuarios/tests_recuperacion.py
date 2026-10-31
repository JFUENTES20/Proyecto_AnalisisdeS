from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import patch
from urllib.parse import urlsplit

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.management import call_command
from django.db import OperationalError
from django.test import Client, RequestFactory, TestCase, override_settings
from django.utils import timezone

from .checks import configuracion_recuperacion
from .models import LimiteRecuperacion, Perfil, SolicitudRecuperacion
from .recuperacion import ip_cliente, procesar_uno


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                   PASSWORD_RESET_PUBLIC_ORIGIN="https://becas.example.test",
                   PASSWORD_RESET_TRUSTED_PROXIES=[], PASSWORD_RESET_IP_LIMIT=20,
                   PASSWORD_RESET_EMAIL_LIMIT=3, PASSWORD_RESET_RATE_WINDOW=900,
                   PASSWORD_RESET_TIMEOUT=3600)
class RecuperacionTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user("recuperacion", "cuenta@example.test", "InicialSoloTest2026!")
        Perfil.objects.create(usuario=self.u, telefono="+50281234567")
        self.original = User.objects.values().get(pk=self.u.pk)

    def solicitar(self, email="cuenta@example.test", client=None, **meta):
        return (client or self.client).post("/recuperar/", {"email": email}, **meta)

    def enviar(self):
        self.solicitar()
        self.assertTrue(procesar_uno())
        return urlsplit(next(l for l in mail.outbox[-1].body.splitlines() if l.startswith("https://"))).path

    def confirmar(self, url, client=None):
        c = client or self.client
        response = c.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("set-password", response.url)
        return response.url

    def test_solicitud_generica_no_envia_en_http_ni_cambia_cuenta(self):
        for email in ("cuenta@example.test", "ausente@example.test"):
            response = self.solicitar(email)
            self.assertRedirects(response, "/recuperar/solicitado/")
        self.assertEqual(SolicitudRecuperacion.objects.count(), 2)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(User.objects.values().get(pk=self.u.pk), self.original)

    def test_flujo_completo_nueva_clave_acceso_y_no_login_automatico(self):
        url = self.enviar()
        self.assertIn("https://becas.example.test/recuperar/", mail.outbox[0].body)
        target = self.confirmar(url)
        response = self.client.post(target, {"new_password1": "NuevaSoloTest2026!", "new_password2": "NuevaSoloTest2026!"})
        self.assertRedirects(response, "/recuperar/completado/")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.u.refresh_from_db(); self.assertTrue(self.u.check_password("NuevaSoloTest2026!"))
        self.assertFalse(self.client.login(username=self.u.username, password="InicialSoloTest2026!"))
        self.assertTrue(self.client.login(username=self.u.username, password="NuevaSoloTest2026!"))
        actual = User.objects.values().get(pk=self.u.pk)
        for field in self.original:
            if field not in {"password", "last_login"}:
                self.assertEqual(actual[field], self.original[field])
        self.assertEqual(self.u.perfil.telefono, "+50281234567")

    def test_enlaces_invalidos_y_uid_invalido(self):
        for url in ("/recuperar/invalido/token/", "/recuperar/OTk5OTk5/token/"):
            response = self.client.get(url)
            self.assertContains(response, "Enlace no válido")
            self.assertNotContains(response, 'name="new_password1"')

    def test_token_vencido(self):
        inicio = datetime(2026, 10, 30, 12, 0)
        with patch.object(default_token_generator, "_now", return_value=inicio):
            url = self.enviar()
        with patch.object(default_token_generator, "_now", return_value=inicio + timedelta(seconds=3601)):
            self.assertContains(self.client.get(url), "Enlace no válido")
        self.u.refresh_from_db(); self.assertEqual(self.u.password, self.original["password"])

    def test_token_reutilizado_no_funciona(self):
        url = self.enviar(); target = self.confirmar(url)
        self.client.post(target, {"new_password1": "NuevaSoloTest2026!", "new_password2": "NuevaSoloTest2026!"})
        self.assertContains(Client().get(url), "Enlace no válido")

    def test_validadores_y_confirmacion_de_clave(self):
        target = self.confirmar(self.enviar())
        for a, b in (("123", "123"), ("NuevaSoloTest2026!", "DiferenteSoloTest2026!")):
            response = self.client.post(target, {"new_password1": a, "new_password2": b})
            self.assertEqual(response.status_code, 200); self.assertTrue(response.context["form"].errors)
        self.u.refresh_from_db(); self.assertEqual(self.u.password, self.original["password"])

    def test_correos_duplicados_incluso_inactivos_se_omiten(self):
        User.objects.create_user("otra", "CUENTA@example.test", "SoloTest2026!", is_active=False)
        self.assertRedirects(self.solicitar(), "/recuperar/solicitado/")
        procesar_uno()
        self.assertEqual(SolicitudRecuperacion.objects.get().estado, "omitido")
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(User.objects.values().get(pk=self.u.pk), self.original)

    def test_inactivo_inutilizable_y_desconocido_no_envian(self):
        self.u.is_active = False; self.u.save()
        self.solicitar(); procesar_uno()
        self.u.is_active = True; self.u.set_unusable_password(); self.u.save()
        self.solicitar(); procesar_uno()
        self.solicitar("desconocida@example.test"); procesar_uno()
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(set(SolicitudRecuperacion.objects.values_list("estado", flat=True)), {"omitido"})

    def test_deteccion_mayusculas_correo_unico(self):
        self.solicitar("CUENTA@EXAMPLE.TEST"); procesar_uno()
        self.assertEqual(len(mail.outbox), 1)

    def test_fallo_smtp_y_cero_aceptados_no_cambian_respuesta_ni_password(self):
        for side_effect in (OSError("detalle privado no debe registrarse"), None):
            response = self.solicitar()
            with patch("usuarios.recuperacion.EmailMultiAlternatives.send", side_effect=side_effect, return_value=0), self.assertLogs("usuarios.recuperacion", level="ERROR") as logs:
                procesar_uno()
            self.assertNotIn("detalle privado", " ".join(logs.output))
            self.assertEqual(response.url, "/recuperar/solicitado/")
        self.assertEqual(set(SolicitudRecuperacion.objects.values_list("estado", flat=True)), {"fallido"})
        self.assertEqual(User.objects.values().get(pk=self.u.pk), self.original)

    @override_settings(PASSWORD_RESET_EMAIL_LIMIT=2)
    def test_limite_correo_compartido_entre_ips_y_respuesta_uniforme(self):
        for i in range(4):
            self.assertEqual(self.solicitar(REMOTE_ADDR=f"192.0.2.{i}").url, "/recuperar/solicitado/")
        self.assertEqual(SolicitudRecuperacion.objects.count(), 2)

    @override_settings(PASSWORD_RESET_IP_LIMIT=2)
    def test_limite_ip_incluye_correos_desconocidos(self):
        for i in range(4):self.solicitar(f"ausente{i}@example.test")
        self.assertEqual(SolicitudRecuperacion.objects.count(), 2)

    @override_settings(PASSWORD_RESET_EMAIL_LIMIT=1)
    def test_ventana_se_renueva_y_no_guarda_email_ip_en_claro(self):
        self.solicitar(); self.solicitar()
        self.assertEqual(SolicitudRecuperacion.objects.count(), 1)
        LimiteRecuperacion.objects.update(ventana=timezone.now()-timedelta(seconds=901))
        self.solicitar(); self.assertEqual(SolicitudRecuperacion.objects.count(), 2)
        self.assertTrue(all(len(c)==64 for c in LimiteRecuperacion.objects.values_list("clave", flat=True)))

    def test_xff_no_se_confia_por_defecto(self):
        request = RequestFactory().get("/", REMOTE_ADDR="192.0.2.10", HTTP_X_FORWARDED_FOR="198.51.100.1")
        self.assertEqual(ip_cliente(request), "192.0.2.10")

    @override_settings(PASSWORD_RESET_TRUSTED_PROXIES=["127.0.0.1", "::1"])
    def test_proxy_confiable_solo_ip_unica_no_cadena_falsificable(self):
        factory = RequestFactory()
        self.assertEqual(ip_cliente(factory.get("/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="198.51.100.2")), "198.51.100.2")
        for xff in ("falso", "198.51.100.2, 192.0.2.3"):
            self.assertEqual(ip_cliente(factory.get("/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR=xff)), "127.0.0.1")

    def test_origen_canonico_no_host_o_forwarded_host_del_cliente(self):
        self.solicitar(HTTP_HOST="localhost", HTTP_X_FORWARDED_HOST="ajeno.example.test")
        procesar_uno(); self.assertIn("https://becas.example.test/", mail.outbox[0].body)
        self.assertNotIn("ajeno.example.test", mail.outbox[0].body)

    def test_csrf_solicitud_y_confirmacion(self):
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(self.solicitar(client=c).status_code, 403)
        url = self.enviar(); target = self.confirmar(url, client=c)
        self.assertEqual(c.post(target, {"new_password1": "NuevaSoloTest2026!", "new_password2": "NuevaSoloTest2026!"}).status_code, 403)

    def test_worker_revalida_email_y_duplicados_antes_de_enviar(self):
        self.solicitar()
        User.objects.create_user("duplicada", self.u.email, "SoloTest2026!")
        procesar_uno(); self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(SolicitudRecuperacion.objects.get().estado, "omitido")

    def test_cambio_email_o_password_antes_worker_omite_solicitud(self):
        for field, value in (("email", "nueva@example.test"), ("password", "inutilizable-distinta")):
            self.solicitar(self.u.email)
            setattr(self.u, field, value); self.u.save()
            procesar_uno()
        self.assertEqual(len(mail.outbox), 0)

    def test_cola_vencida_no_genera_token_tardio(self):
        self.solicitar(); SolicitudRecuperacion.objects.update(creada=timezone.now()-timedelta(seconds=3601))
        procesar_uno(); self.assertEqual(len(mail.outbox), 0)

    def test_fallo_base_no_revela_usuario(self):
        with patch("usuarios.recuperacion.permitido", side_effect=OperationalError), self.assertLogs("usuarios.recuperacion", level="ERROR"):
            self.assertEqual(self.solicitar().url, "/recuperar/solicitado/")

    def test_worker_comando_no_confirma_bandeja_y_cola_vacia(self):
        self.solicitar(); out = StringIO()
        call_command("procesar_recuperaciones", stdout=out)
        self.assertIn("no confirma entrega", out.getvalue())
        self.assertFalse(procesar_uno())

    def test_configuracion_invalida_detectada(self):
        with override_settings(EMAIL_USE_TLS=True, EMAIL_USE_SSL=True, PASSWORD_RESET_EMAIL_LIMIT=0,
                PASSWORD_RESET_TRUSTED_PROXIES=["cualquierproxy"], PASSWORD_RESET_PUBLIC_ORIGIN="https://host.example.test/ruta"):
            self.assertEqual({e.id for e in configuracion_recuperacion(None)}, {"usuarios.E001", "usuarios.E002", "usuarios.E003", "usuarios.E004"})

    def test_pantallas_y_enlace_discreto(self):
        self.assertContains(self.client.get("/acceso/"), "¿Olvidaste tu contraseña?")
        for url in ("/recuperar/", "/recuperar/solicitado/", "/recuperar/completado/"):
            self.assertEqual(self.client.get(url).status_code, 200)


    def test_correo_ambiguo_despues_de_emitir_invalida_confirmacion(self):
        url = self.enviar()
        User.objects.create_user("nueva-duplicada", self.u.email, "SoloTest2026!")
        self.assertContains(self.client.get(url), "Enlace no válido")
        self.u.refresh_from_db(); self.assertEqual(self.u.password, self.original["password"])

    def test_cuenta_inactivada_despues_de_emitir_no_confirma(self):
        url = self.enviar(); self.u.is_active = False; self.u.save()
        self.assertContains(self.client.get(url), "Enlace no válido")

    def test_token_no_permite_otra_cuenta(self):
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        otro = User.objects.create_user("otra-cuenta", "otra@example.test", "SoloTest2026!")
        url = self.enviar(); partes = url.split("/")
        partes[2] = urlsafe_base64_encode(force_bytes(otro.pk))
        self.assertContains(self.client.get("/".join(partes)), "Enlace no válido")


    @override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
                       EMAIL_HOST="smtp.example.test", EMAIL_PORT=587,
                       EMAIL_HOST_USER="usuario-sintetico", EMAIL_HOST_PASSWORD="solo-configuracion-de-test",
                       EMAIL_USE_TLS=True, EMAIL_USE_SSL=False, EMAIL_TIMEOUT=10)
    def test_smtp_configurado_starttls_autenticacion_sin_red(self):
        with patch("django.core.mail.backends.smtp.smtplib.SMTP") as smtp:
            smtp.return_value.sendmail.return_value = {}
            self.solicitar(); procesar_uno()
            smtp.assert_called_once_with("smtp.example.test", 587, local_hostname=smtp.call_args.kwargs["local_hostname"], timeout=10)
            smtp.return_value.starttls.assert_called_once()
            smtp.return_value.login.assert_called_once_with("usuario-sintetico", "solo-configuracion-de-test")
            smtp.return_value.sendmail.assert_called_once()
        self.assertEqual(SolicitudRecuperacion.objects.get().estado, "aceptado")
        self.assertEqual(User.objects.values().get(pk=self.u.pk), self.original)

    def test_error_smtp_se_registra_sin_exponer_detalles(self):
        from smtplib import SMTPException
        self.solicitar()
        with patch("usuarios.recuperacion.EmailMultiAlternatives.send", side_effect=SMTPException("detalle privado")), self.assertLogs("usuarios.recuperacion", level="ERROR") as logs:
            procesar_uno()
        self.assertNotIn("detalle privado", " ".join(logs.output))
        self.assertEqual(SolicitudRecuperacion.objects.get().estado, "fallido")
