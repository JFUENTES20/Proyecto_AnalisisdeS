from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from .contacto import actualizar_telefono, hay_discrepancia, normalizar_telefono, version_contacto
from .models import Aspirante, EventoContacto, Perfil


class ContactoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("contacto", "contacto@example.test", "SoloTest123!")
        self.perfil = Perfil.objects.create(usuario=self.user, telefono="+50251234567")
        self.otro = User.objects.create_user("otro")
        self.ajeno = Perfil.objects.create(usuario=self.otro, telefono="+50261234567")
        self.client.force_login(self.user)

    def datos(self, **extra):
        return {"telefono": "+502 2345 6789", "version": version_contacto(self.perfil), **extra}

    def test_normalizacion_y_numeros_invalidos(self):
        for valor in ("51234567", " 5123 4567 ", "+502 5123 4567", "+502\u00a051234567"):
            self.assertEqual(normalizar_telefono(valor), "+50251234567")
        for valor in ("", "12345678", "81234567", "91234567", "5123456", "512345678", "+50351234567", "50251234567", "abcd1234", "５１２３４５６７"):
            with self.subTest(valor=valor), self.assertRaises(ValidationError):
                normalizar_telefono(valor)

    def test_anonimo_y_roles_no_autorizados(self):
        self.client.logout()
        self.assertEqual(self.client.get("/mi-perfil/").status_code, 302)
        self.assertEqual(self.client.post("/mi-perfil/", self.datos()).status_code, 302)
        self.client.force_login(self.user)
        for rol in ("evaluador", "aprobador", "administrador"):
            self.perfil.rol = rol
            self.perfil.save()
            self.assertEqual(self.client.get("/mi-perfil/").status_code, 403)
            self.assertEqual(self.client.post("/mi-perfil/", self.datos()).status_code, 403)

    def test_consulta_no_cambia_datos_y_muestra_navegacion(self):
        self.assertContains(self.client.get("/mi-perfil/"), "Mi perfil")
        self.assertContains(self.client.get("/panel/"), 'href="/mi-perfil/"')
        self.assertFalse(EventoContacto.objects.exists())
        self.assertFalse(Aspirante.objects.exists())

    def test_actualiza_solo_telefono_y_audita(self):
        historico = Aspirante.objects.create(user=self.user, cedula="TEST-1", telefono="51234567")
        usuario = User.objects.values().get(pk=self.user.pk)
        legado = Aspirante.objects.values().get(pk=historico.pk)
        self.assertEqual(self.client.post("/mi-perfil/", self.datos()).status_code, 302)
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.telefono, "+50223456789")
        self.assertEqual(User.objects.values().get(pk=self.user.pk), usuario)
        self.assertEqual(Aspirante.objects.values().get(pk=historico.pk), legado)
        evento = EventoContacto.objects.get()
        self.assertEqual((evento.responsable_id, evento.telefono_anterior, evento.telefono_nuevo), (self.user.pk, "+50251234567", "+50223456789"))
        self.assertEqual((evento.operacion, evento.resultado), ("actualizar_telefono", "actualizado"))
        self.assertIsNotNone(evento.fecha)

    def test_rechaza_campos_ajenos_y_version_de_otro_perfil(self):
        for campo in ("perfil_id", "usuario_id", "email", "rol", "password", "cedula"):
            self.assertEqual(self.client.post("/mi-perfil/", self.datos(**{campo: str(self.otro.pk)})).status_code, 403)
        self.assertEqual(self.client.post("/mi-perfil/", self.datos(version=version_contacto(self.ajeno))).status_code, 200)
        self.ajeno.refresh_from_db()
        self.assertEqual(self.ajeno.telefono, "+50261234567")
        self.assertFalse(EventoContacto.objects.exists())

    def test_discrepancia_exige_confirmacion_y_conserva_historico(self):
        Aspirante.objects.create(user=self.user, cedula="TEST-2", telefono="61234567")
        self.assertContains(self.client.post("/mi-perfil/", self.datos()), "Confirma el teléfono")
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.telefono, "+50251234567")
        self.assertEqual(self.client.post("/mi-perfil/", self.datos(confirmar_cambio="on")).status_code, 302)
        self.assertEqual(Aspirante.objects.get(user=self.user).telefono, "61234567")

    def test_no_rellena_canonico_vacio_silenciosamente(self):
        self.perfil.telefono = ""
        self.perfil.save()
        Aspirante.objects.create(user=self.user, cedula="TEST-3", telefono="51234567")
        self.client.get("/mi-perfil/")
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.telefono, "")
        self.assertTrue(hay_discrepancia("", "51234567"))
        self.assertFalse(hay_discrepancia("+50251234567", "5123 4567"))

    def test_formulario_obsoleto_o_alterado_no_sobrescribe(self):
        version = version_contacto(self.perfil)
        self.perfil.telefono = "+50271234567"
        self.perfil.save()
        for token in (version, "alterado"):
            with self.assertRaises(ValidationError):
                actualizar_telefono(self.user, "23456789", token)
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.telefono, "+50271234567")

    def test_invalido_no_guarda_y_repetir_no_duplica_auditoria(self):
        self.assertContains(self.client.post("/mi-perfil/", self.datos(telefono="123")), "8 dígitos")
        self.assertFalse(EventoContacto.objects.exists())
        actualizar_telefono(self.user, "23456789", version_contacto(self.perfil))
        self.perfil.refresh_from_db()
        self.assertFalse(actualizar_telefono(self.user, "23456789", version_contacto(self.perfil)))
        self.assertEqual(EventoContacto.objects.count(), 1)

    def test_fallo_auditoria_revierte_cambio(self):
        with patch("usuarios.contacto.EventoContacto.objects.create", side_effect=RuntimeError("fallo")):
            with self.assertRaises(RuntimeError):
                actualizar_telefono(self.user, "23456789", version_contacto(self.perfil))
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.telefono, "+50251234567")

    def test_post_exige_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post("/mi-perfil/", self.datos()).status_code, 403)
