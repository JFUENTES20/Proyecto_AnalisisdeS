import tempfile
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from convocatorias.models import Convocatoria
from evaluaciones.models import Comite
from usuarios.models import Perfil
from .forms import DocumentoForm
from .models import Solicitud, Documento, Notificacion
from .patterns import NotificacionObserver
from .reportes import ReporteBuilder, ExportadorCSV
from .services import ExpedienteFacade


class FlujoBecasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        def usuario(nombre, rol):
            u = User.objects.create_user(
                username=nombre,
                password="ClaveDePrueba123!",
                email=nombre + "@example.com",
            )
            Perfil.objects.create(usuario=u, rol=rol)
            return u

        cls.aspirante = usuario("ana", "aspirante")
        cls.otro = usuario("otro", "aspirante")
        cls.evaluador = usuario("evaluador", "evaluador")
        cls.no_asignado = usuario("externo", "evaluador")
        cls.aprobador = usuario("aprobador1", "aprobador")
        cls.aprobador2 = usuario("aprobador2", "aprobador")
        hoy = timezone.localdate()
        cls.convocatoria = Convocatoria.objects.create(
            titulo="Beca universitaria",
            descripcion="Prueba",
            requisitos="Constancia",
            nivel="universitario",
            apertura=hoy - timedelta(days=1),
            cierre=hoy + timedelta(days=10),
            monto_maximo=Decimal("20000"),
            publicada=True,
        )
        comite = Comite.objects.create(
            nombre="Comité de pruebas", convocatoria=cls.convocatoria
        )
        comite.miembros.add(cls.evaluador)

    def crear(self, monto="12000"):
        return ExpedienteFacade.crear(
            self.aspirante,
            self.convocatoria,
            Decimal(monto),
            "Motivación suficiente para la prueba del expediente.",
        )

    def en_revision(self, monto="12000"):
        s = self.crear(monto)
        Documento.objects.create(
            solicitud=s,
            nombre="Constancia",
            archivo="prueba.pdf",
            cargado_por=self.aspirante,
        )
        ExpedienteFacade.transicionar(self.aspirante, s.pk, "enviar")
        ExpedienteFacade.transicionar(
            self.evaluador, s.pk, "revisar", "Inicio de revisión documental."
        )
        ExpedienteFacade.evaluar(
            self.evaluador, s.pk, 90, "Cumple los criterios académicos."
        )
        return s

    def test_monto_superior_requiere_dos_personas(self):
        s = self.en_revision()
        primera = ExpedienteFacade.transicionar(
            self.aprobador, s.pk, "aprobar", "Primera aprobación."
        )
        self.assertEqual(primera.estado, "segunda_aprobacion")
        with self.assertRaises(ValidationError):
            ExpedienteFacade.transicionar(
                self.aprobador, s.pk, "aprobar", "Intento repetido."
            )
        final = ExpedienteFacade.transicionar(
            self.aprobador2, s.pk, "aprobar", "Segunda aprobación."
        )
        self.assertEqual(final.estado, "aprobada")
        self.assertEqual(final.decisiones.filter(accion="aprobar").count(), 2)

    def test_exactamente_diez_mil_solo_una_aprobacion(self):
        s = self.en_revision("10000")
        s = ExpedienteFacade.transicionar(
            self.aprobador, s.pk, "aprobar", "Aprobación del expediente."
        )
        self.assertEqual(s.estado, "aprobada")

    def test_monto_inferior_solo_una_aprobacion(self):
        s = self.en_revision("9999.99")
        s = ExpedienteFacade.transicionar(
            self.aprobador, s.pk, "aprobar", "Aprobación del expediente."
        )
        self.assertEqual(s.estado, "aprobada")

    def test_no_enviar_sin_documentos(self):
        s = self.crear()
        with self.assertRaises(ValidationError):
            ExpedienteFacade.transicionar(self.aspirante, s.pk, "enviar")
        s.refresh_from_db()
        self.assertEqual(s.estado, "borrador")

    def test_no_autorizacion_directa_desde_borrador(self):
        s = self.crear()
        with self.assertRaises(ValidationError):
            ExpedienteFacade.transicionar(
                self.aprobador, s.pk, "aprobar", "Salto de estado."
            )

    def test_no_aprobar_sin_evaluacion(self):
        s = self.crear()
        s.estado = "revision"
        s.save()
        with self.assertRaises(ValidationError):
            ExpedienteFacade.transicionar(
                self.aprobador, s.pk, "aprobar", "Sin evaluación."
            )

    def test_no_solicitudes_duplicadas(self):
        self.crear()
        with self.assertRaises(ValidationError):
            self.crear()

    def test_no_monto_superior_al_maximo(self):
        with self.assertRaises(ValidationError):
            self.crear("20000.01")

    def test_convocatoria_cerrada_no_admite_solicitud(self):
        self.convocatoria.publicada = False
        self.convocatoria.save()
        with self.assertRaises(ValidationError):
            self.crear()

    def test_aspirante_no_aprueba(self):
        s = self.en_revision()
        with self.assertRaises(PermissionDenied):
            ExpedienteFacade.transicionar(
                self.aspirante, s.pk, "aprobar", "Autorización propia."
            )

    def test_evaluador_no_asignado_no_revisa(self):
        s = self.en_revision()
        with self.assertRaises(PermissionDenied):
            ExpedienteFacade.evaluar(
                self.no_asignado, s.pk, 99, "Sin asignación de comité."
            )

    def test_eventos_y_avisos_persistidos(self):
        s = self.en_revision()
        self.assertTrue(
            s.eventos.filter(
                actor=self.evaluador,
                operacion="revisar",
                anterior="pendiente",
                resultado="revision",
            ).exists()
        )
        self.assertEqual(
            Notificacion.objects.filter(destinatario=self.aspirante).count(), 2
        )
        self.assertTrue(
            Notificacion.objects.filter(destinatario=self.evaluador).exists()
        )
        self.assertFalse(
            Notificacion.objects.filter(destinatario=self.no_asignado).exists()
        )

    def test_fallo_observador_revierte_decision_estado_y_auditoria(self):
        s = self.en_revision()
        eventos = s.eventos.count()
        with patch.object(
            NotificacionObserver,
            "actualizar",
            side_effect=RuntimeError("fallo simulado"),
        ):
            with self.assertRaises(RuntimeError):
                ExpedienteFacade.transicionar(
                    self.aprobador, s.pk, "aprobar", "Intento atómico."
                )
        s.refresh_from_db()
        self.assertEqual(s.estado, "revision")
        self.assertEqual(s.eventos.count(), eventos)
        self.assertFalse(s.decisiones.filter(accion="aprobar").exists())

    def test_solicitud_ajena_no_es_visible(self):
        s = self.crear()
        self.client.force_login(self.otro)
        self.assertEqual(
            self.client.get(reverse("solicitud_detalle", args=[s.pk])).status_code, 403
        )
        self.assertNotContains(
            self.client.get(reverse("solicitudes_list")), self.aspirante.email
        )

    def test_no_modificar_por_get(self):
        s = self.crear()
        self.client.force_login(self.aspirante)
        self.assertEqual(
            self.client.get(reverse("cambiar_estado", args=[s.pk])).status_code, 405
        )

    def test_no_descargar_documento_ajeno(self):
        s = self.crear()
        doc = Documento.objects.create(
            solicitud=s,
            nombre="Privado",
            archivo="privado.pdf",
            cargado_por=self.aspirante,
        )
        self.client.force_login(self.otro)
        self.assertEqual(
            self.client.get(reverse("descargar_documento", args=[doc.pk])).status_code,
            403,
        )

    def test_no_marcar_aviso_ajeno(self):
        self.en_revision()
        n = self.aspirante.notificaciones.first()
        self.client.force_login(self.otro)
        self.assertEqual(
            self.client.post(reverse("leer_notificacion", args=[n.pk])).status_code, 404
        )
        n.refresh_from_db()
        self.assertFalse(n.leida)

    def test_documento_valida_contenido_no_solo_extension(self):
        form = DocumentoForm(
            {"nombre": "Falso PDF"},
            {"archivo": SimpleUploadedFile("falso.pdf", b"<html>malicioso</html>")},
        )
        self.assertFalse(form.is_valid())

    def test_carga_y_descarga_autorizada(self):
        s = self.crear()
        self.client.force_login(self.aspirante)
        with (
            tempfile.TemporaryDirectory() as directorio,
            override_settings(MEDIA_ROOT=directorio),
        ):
            archivo = SimpleUploadedFile("constancia.pdf", b"%PDF-1.4\nprueba")
            self.client.post(
                reverse("adjuntar", args=[s.pk]),
                {"nombre": "Constancia", "archivo": archivo},
            )
            doc = s.documentos.get()
            respuesta = self.client.get(reverse("descargar_documento", args=[doc.pk]))
            self.assertEqual(respuesta.status_code, 200)
            self.assertIn("attachment;", respuesta["Content-Disposition"])
            self.assertEqual(b"".join(respuesta.streaming_content), b"%PDF-1.4\nprueba")
            self.assertTrue(s.eventos.filter(operacion="documento").exists())

    def test_solicitar_correcciones_y_reenviar(self):
        s = self.en_revision()
        ExpedienteFacade.transicionar(
            self.evaluador, s.pk, "corregir", "Adjunta constancia legible."
        )
        self.client.force_login(self.aspirante)
        self.assertContains(
            self.client.get(reverse("solicitud_detalle", args=[s.pk])),
            "Adjunta constancia legible.",
        )
        s = ExpedienteFacade.transicionar(self.aspirante, s.pk, "enviar")
        self.assertEqual(s.estado, "pendiente")

    def test_rechazo_tiene_motivo_y_estado_terminal(self):
        s = self.en_revision()
        s = ExpedienteFacade.transicionar(
            self.aprobador,
            s.pk,
            "rechazar",
            "No cumple los requisitos de la convocatoria.",
        )
        self.assertEqual(s.estado, "rechazada")
        with self.assertRaises(ValidationError):
            ExpedienteFacade.transicionar(
                self.aprobador2, s.pk, "aprobar", "Intento posterior."
            )

    def test_reportes_solo_personal_autorizado(self):
        self.crear()
        self.client.force_login(self.aspirante)
        self.assertEqual(self.client.get(reverse("reporte_csv")).status_code, 403)
        self.client.force_login(self.aprobador)
        respuesta = self.client.get(reverse("reporte_csv"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Expediente", status_code=200)
        self.assertNotContains(respuesta, self.aspirante.email)

    def test_reporte_neutraliza_formulas_csv(self):
        self.convocatoria.titulo = "=1+1"
        self.convocatoria.save()
        self.crear()
        reporte = (
            ReporteBuilder(Solicitud.objects.all())
            .identificacion()
            .seguimiento()
            .construir()
        )
        self.assertIn("'=1+1", ExportadorCSV().exportar(reporte))

    def test_paginas_principales_renderizan(self):
        for url in ("inicio", "login", "registro"):
            self.assertEqual(self.client.get(reverse(url)).status_code, 200)
        self.assertEqual(
            self.client.get(
                reverse("convocatoria_detalle", args=[self.convocatoria.pk])
            ).status_code,
            200,
        )
        self.client.force_login(self.aspirante)
        for url in ("panel", "solicitudes_list", "notificaciones"):
            self.assertEqual(self.client.get(reverse(url)).status_code, 200)

    def test_registro_no_permite_elegir_rol_privilegiado(self):
        respuesta = self.client.post(
            reverse("registro"),
            {
                "username": "nueva",
                "first_name": "Nueva",
                "last_name": "Persona",
                "email": "NUEVA@example.com",
                "password1": "SeguraLarga123!",
                "password2": "SeguraLarga123!",
                "rol": "administrador",
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        usuario = User.objects.get(username="nueva")
        self.assertEqual(usuario.perfil.rol, "aspirante")
        self.assertEqual(usuario.email, "nueva@example.com")
        self.assertFalse(usuario.is_staff)

    def test_correcciones_invalidan_evaluacion_y_exigen_reevaluar(self):
        s = self.en_revision()
        ExpedienteFacade.transicionar(
            self.evaluador, s.pk, "corregir", "Completar documentación académica."
        )
        self.assertFalse(s.evaluaciones.get().vigente)
        ExpedienteFacade.transicionar(self.aspirante, s.pk, "enviar")
        ExpedienteFacade.transicionar(
            self.evaluador, s.pk, "revisar", "Nueva revisión tras correcciones."
        )
        with self.assertRaises(ValidationError):
            ExpedienteFacade.transicionar(
                self.aprobador, s.pk, "aprobar", "No debe usar evaluación anterior."
            )
        ExpedienteFacade.evaluar(
            self.evaluador, s.pk, 92, "Documentación corregida y revisada."
        )
        self.assertEqual(s.evaluaciones.count(), 2)
        self.assertEqual(s.evaluaciones.filter(vigente=True).count(), 1)

    def test_edicion_se_registra_sin_cambiar_estado(self):
        s = self.crear()
        s = ExpedienteFacade.editar(
            self.aspirante,
            s.pk,
            Decimal("8000"),
            "Nueva motivación para la solicitud de beca.",
        )
        self.assertEqual(s.monto, Decimal("8000"))
        self.assertEqual(s.estado, "borrador")
        self.assertTrue(s.eventos.filter(operacion="editar").exists())

    def test_no_editar_despues_de_enviar(self):
        s = self.en_revision()
        with self.assertRaises(ValidationError):
            ExpedienteFacade.editar(
                self.aspirante, s.pk, Decimal("5000"), "Cambios fuera de estado."
            )

    def test_personal_no_puede_autoevaluar(self):
        s = self.en_revision()
        s.aspirante = self.evaluador
        s.save()
        with self.assertRaises(PermissionDenied):
            ExpedienteFacade.evaluar(
                self.evaluador, s.pk, 100, "Evaluación propia no permitida."
            )

    def test_sin_justificacion_no_hay_decision(self):
        s = self.en_revision()
        with self.assertRaises(ValidationError):
            ExpedienteFacade.transicionar(self.aprobador, s.pk, "rechazar", "   ")
        self.assertFalse(s.decisiones.filter(accion="rechazar").exists())

    def test_seguimiento_beca_aprobada_activa_completada(self):
        s = self.en_revision("8000")
        ExpedienteFacade.transicionar(
            self.aprobador, s.pk, "aprobar", "Aprobación inicial."
        )
        ExpedienteFacade.transicionar(
            self.aprobador, s.pk, "activar", "Inicio del período de beca."
        )
        s = ExpedienteFacade.transicionar(
            self.aprobador, s.pk, "completar", "Finalización del período académico."
        )
        self.assertEqual(s.estado, "completada")
        self.assertEqual(s.eventos.filter(operacion="completar").count(), 1)

    def test_formulario_de_decision_requiere_csrf(self):
        from django.test import Client

        s = self.en_revision()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.aprobador)
        respuesta = client.post(
            reverse("cambiar_estado", args=[s.pk]),
            {"accion": "aprobar", "comentario": "Sin token CSRF."},
        )
        self.assertEqual(respuesta.status_code, 403)

    def test_cuentas_inactivas_no_reciben_avisos_operativos(self):
        self.evaluador.is_active = False
        self.evaluador.save()
        self.en_revision()
        self.assertFalse(
            Notificacion.objects.filter(destinatario=self.evaluador).exists()
        )
