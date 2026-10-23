import os
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from evaluaciones.models import Comite
from .models import Convocatoria
from solicitudes.management.commands.seed_demo import CONVOCATORIAS_DEMO, DESCRIPCION_DEMO_ANTERIOR


class TextosDemoTests(TestCase):
    def crear(self, titulo, nivel, descripcion):
        hoy = timezone.localdate()
        return Convocatoria.objects.create(
            titulo=titulo, nivel=nivel, descripcion=descripcion,
            requisitos="Requisito personalizado conservado.", monto_maximo=Decimal("12345.67"),
            apertura=hoy-timedelta(days=1), cierre=hoy+timedelta(days=8), publicada=False,
        )

    def actualizar(self):
        with patch.dict(os.environ, {"DEMO_PASSWORD": ""}):
            call_command("seed_demo", actualizar_textos=True, stdout=StringIO())

    def test_actualiza_solo_descripcion_y_es_idempotente(self):
        for titulo, nivel, _, _ in CONVOCATORIAS_DEMO:
            self.crear(titulo, nivel, DESCRIPCION_DEMO_ANTERIOR)
        antes = list(Convocatoria.objects.order_by("pk").values())
        self.actualizar()
        despues = list(Convocatoria.objects.order_by("pk").values())
        esperadas = {titulo: descripcion for titulo, _, _, descripcion in CONVOCATORIAS_DEMO}
        for old, new in zip(antes, despues):
            self.assertEqual(new["descripcion"], esperadas[new["titulo"]])
            self.assertEqual({k:v for k,v in old.items() if k!="descripcion"},
                             {k:v for k,v in new.items() if k!="descripcion"})
        self.actualizar()
        self.assertEqual(list(Convocatoria.objects.order_by("pk").values()), despues)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Comite.objects.count(), 0)

    def test_respeta_personalizados_titulos_ajenos_y_nivel_distinto(self):
        titulo, nivel, _, _ = CONVOCATORIAS_DEMO[0]
        self.crear(titulo, nivel, "Descripción personalizada por el equipo.")
        self.crear("Otra convocatoria", nivel, DESCRIPCION_DEMO_ANTERIOR)
        self.crear(titulo, "medio", DESCRIPCION_DEMO_ANTERIOR)
        # Un texto parecido, pero no idéntico al ejemplo, tampoco se reemplaza.
        self.crear(CONVOCATORIAS_DEMO[1][0], "medio", DESCRIPCION_DEMO_ANTERIOR + " Nota del equipo.")
        antes = list(Convocatoria.objects.order_by("pk").values())
        self.actualizar()
        self.assertEqual(list(Convocatoria.objects.order_by("pk").values()), antes)

    def test_actualizar_no_crea_convocatorias_faltantes(self):
        self.actualizar()
        self.assertEqual(Convocatoria.objects.count(), 0)
        self.assertEqual(User.objects.count(), 0)

    def test_generador_nuevo_y_repetido_conserva_personalizados(self):
        with patch.dict(os.environ, {"DEMO_PASSWORD": "SoloPruebaLocal2026!"}):
            call_command("seed_demo", stdout=StringIO())
            self.assertEqual(Convocatoria.objects.count(), 3)
            for titulo, nivel, monto, descripcion in CONVOCATORIAS_DEMO:
                c = Convocatoria.objects.get(titulo=titulo)
                self.assertEqual(c.descripcion, descripcion)
                self.assertEqual(c.nivel, nivel)
                self.assertEqual(c.monto_maximo, Decimal(monto))
                self.assertEqual(c.requisitos, "Constancia de estudios.\nCertificación de notas.\nCarta de motivación.")
                self.assertEqual(c.apertura, timezone.localdate()-timedelta(days=3))
                self.assertEqual(c.cierre, timezone.localdate()+timedelta(days=45))
            c = Convocatoria.objects.first()
            c.descripcion = "Texto propio del equipo."
            c.save(update_fields=["descripcion"])
            antes = list(Convocatoria.objects.order_by("pk").values())
            call_command("seed_demo", stdout=StringIO())
            self.assertEqual(list(Convocatoria.objects.order_by("pk").values()), antes)
