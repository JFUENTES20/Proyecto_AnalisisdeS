import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from .fotografia import MAX_BYTES, cambiar_fotografia
from .models import Aspirante, EventoFotografia, Perfil


def imagen(formato="PNG", size=(640, 480), **save):
    stream = BytesIO()
    Image.new("RGB", size, "#087f70").save(stream, formato, **save)
    return SimpleUploadedFile("ejemplo." + ("jpg" if formato == "JPEG" else formato.lower()), stream.getvalue(), content_type="application/octet-stream")


class FotografiaTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings_media = override_settings(MEDIA_ROOT=self.temp.name)
        self.settings_media.enable()
        self.addCleanup(self.settings_media.disable)
        self.usuario = User.objects.create_user("foto", first_name="Ana", last_name="Prueba")
        self.perfil = Perfil.objects.create(usuario=self.usuario, telefono="+50281234567")
        self.otro = User.objects.create_user("otra")
        self.ajeno = Perfil.objects.create(usuario=self.otro)
        self.client.force_login(self.usuario)
        self.url = "/mi-perfil/fotografia/"
        self.ver = f"/mi-perfil/fotografia/{self.usuario.pk}/"

    def subir(self, archivo=None, **extra):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(self.url, {"accion": "guardar", "fotografia": archivo or imagen(), **extra}, follow=True)

    def test_encabezado_sin_foto_es_opcional(self):
        response = self.client.get("/mi-perfil/")
        self.assertContains(response, "Ana Prueba")
        self.assertContains(response, "foto</strong>")
        self.assertContains(response, "AP</span>")
        self.assertContains(response, "Puedes solicitar becas sin añadir")
        self.assertEqual(self.client.get(self.ver).status_code, 404)

    def test_iniciales_sin_nombre_usan_usuario_sin_cambiarlo(self):
        self.usuario.first_name = self.usuario.last_name = ""
        self.usuario.save()
        self.assertContains(self.client.get("/mi-perfil/"), "F</span>")

    def test_sube_png_jpeg_real_y_optimiza(self):
        for formato in ("PNG", "JPEG"):
            with self.subTest(formato=formato):
                self.assertContains(self.subir(imagen(formato)), "Fotografía actualizada")
                self.perfil.refresh_from_db()
                with Image.open(self.perfil.fotografia.path) as img:
                    self.assertEqual((img.format, img.size), ("JPEG", (512, 512)))
                    self.assertFalse(img.getexif())
                self.assertLess(self.perfil.fotografia.size, MAX_BYTES)

    def test_orientacion_y_eliminacion_exif(self):
        stream = BytesIO()
        img = Image.new("RGB", (100, 60), "red")
        img.paste("blue", (50, 0, 100, 60))
        exif = Image.Exif(); exif[274] = 6; exif[315] = "Solo prueba"
        img.save(stream, "JPEG", exif=exif)
        self.subir(SimpleUploadedFile("rotada.jpg", stream.getvalue()))
        self.perfil.refresh_from_db()
        with Image.open(self.perfil.fotografia.path) as img:
            self.assertFalse(img.getexif())
            arriba, abajo = img.getpixel((256, 32)), img.getpixel((256, 480))
            self.assertGreater(arriba[0], arriba[2])
            self.assertGreater(abajo[2], abajo[0])

    def test_transparencia_sobre_blanco(self):
        b = BytesIO(); Image.new("RGBA", (40, 40), (0, 0, 0, 0)).save(b, "PNG")
        self.subir(SimpleUploadedFile("alpha.png", b.getvalue()))
        self.perfil.refresh_from_db()
        with Image.open(self.perfil.fotografia.path) as img:
            self.assertEqual(img.getpixel((0, 0)), (255, 255, 255))

    def test_reemplazo_y_eliminacion_limpian_archivos_y_auditan(self):
        self.subir(); self.perfil.refresh_from_db(); anterior = self.perfil.fotografia.path
        self.subir(imagen("JPEG")); self.perfil.refresh_from_db(); nuevo = self.perfil.fotografia.path
        self.assertNotEqual(anterior, nuevo); self.assertFalse(Path(anterior).exists())
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post(self.url, {"accion": "eliminar"}).status_code, 302)
        self.perfil.refresh_from_db()
        self.assertFalse(self.perfil.fotografia); self.assertFalse(Path(nuevo).exists())
        self.assertEqual(self.client.get(self.ver).status_code, 404)
        self.assertEqual(list(EventoFotografia.objects.order_by("pk").values_list("operacion", flat=True)), ["subir", "reemplazar", "eliminar"])
        self.assertTrue(all(e.responsable_id == self.usuario.pk and e.fecha and e.resultado == "actualizado" for e in EventoFotografia.objects.all()))
        self.assertContains(self.client.get("/mi-perfil/"), "AP</span>")

    def test_eliminar_sin_foto_no_duplica_eventos(self):
        self.client.post(self.url, {"accion": "eliminar"})
        self.assertFalse(EventoFotografia.objects.exists())

    def test_rechaza_invalido_gif_y_extension(self):
        for archivo in (SimpleUploadedFile("falsa.jpg", b"no es imagen"), imagen("GIF"),
                        SimpleUploadedFile("falsa.png", b"%PDF-1.4"),
                        SimpleUploadedFile("archivo.svg", imagen().read())):
            with self.subTest(nombre=archivo.name):
                self.assertContains(self.subir(archivo), "JPG o PNG")
        self.assertFalse(EventoFotografia.objects.exists())

    def test_rechaza_jpeg_truncado_y_conserva_foto(self):
        self.subir(); self.perfil.refresh_from_db(); anterior = self.perfil.fotografia.name
        datos = imagen("JPEG").read()[:-80]
        self.assertContains(self.subir(SimpleUploadedFile("rota.jpg", datos)), "dañado")
        self.perfil.refresh_from_db(); self.assertEqual(self.perfil.fotografia.name, anterior)

    def test_limite_bytes_y_dimensiones(self):
        self.assertContains(self.subir(SimpleUploadedFile("grande.jpg", b"x" * (MAX_BYTES + 1))), "2 MB")
        self.assertContains(self.subir(imagen(size=(6001, 1))), "6000")
        self.assertContains(self.subir(imagen(size=(4000, 3001))), "12 megapíxeles")
        self.assertFalse(self.perfil.fotografia)

    def test_rechaza_png_animado(self):
        b = BytesIO()
        Image.new("RGB", (10, 10), "red").save(b, "PNG", save_all=True, append_images=[Image.new("RGB", (10, 10), "blue")])
        self.assertContains(self.subir(SimpleUploadedFile("animada.png", b.getvalue())), "sin animación")

    def test_servicio_no_confia_en_mime(self):
        archivo = SimpleUploadedFile("falso.jpg", b"<script>hola</script>", content_type="image/jpeg")
        self.assertContains(self.subir(archivo), "JPG o PNG")

    def test_acceso_privado_y_no_ruta_media(self):
        self.subir(); self.perfil.refresh_from_db()
        response = self.client.get(self.ver)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertTrue(b"".join(response.streaming_content).startswith(b"\xff\xd8"))
        self.assertEqual(self.client.get("/media/" + self.perfil.fotografia.name).status_code, 404)
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(self.ver).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(self.ver).status_code, 302)
        self.assertEqual(self.client.post(self.url, {"accion": "eliminar"}).status_code, 302)

    def test_solo_modifica_cuenta_propia_y_rechaza_campos_extra(self):
        for campo in ("usuario_id", "perfil_id", "email", "rol", "telefono", "password"):
            self.assertEqual(self.client.post(self.url, {"accion": "eliminar", campo: self.otro.pk}).status_code, 403)
        self.ajeno.refresh_from_db(); self.assertFalse(self.ajeno.fotografia)
        self.assertFalse(EventoFotografia.objects.exists())

    def test_no_modifica_identidad_telefono_ni_historico(self):
        Aspirante.objects.create(user=self.usuario, cedula="TEST-FOTO", telefono="55550000")
        old_user = User.objects.values().get(pk=self.usuario.pk)
        old_asp = Aspirante.objects.values().get(user=self.usuario)
        self.subir()
        self.assertEqual(User.objects.values().get(pk=self.usuario.pk), old_user)
        self.assertEqual(Aspirante.objects.values().get(user=self.usuario), old_asp)
        self.perfil.refresh_from_db(); self.assertEqual(self.perfil.telefono, "+50281234567")

    def test_roles_csrf_metodo_y_archivo_faltante(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        csrf = Client(enforce_csrf_checks=True); csrf.force_login(self.usuario)
        self.assertEqual(csrf.post(self.url, {"accion": "eliminar"}).status_code, 403)
        self.assertContains(self.client.post(self.url, {"accion": "guardar"}, follow=True), "Este campo es obligatorio")
        for rol in ("evaluador", "aprobador", "administrador"):
            self.perfil.rol = rol; self.perfil.save()
            self.assertEqual(self.client.post(self.url, {"accion": "eliminar"}).status_code, 403)

    def test_fallo_auditoria_revierte_base_y_limpia_nuevo(self):
        self.subir(); self.perfil.refresh_from_db(); anterior = self.perfil.fotografia.name
        with patch("usuarios.fotografia.EventoFotografia.objects.create", side_effect=RuntimeError("fallo")):
            with self.assertRaises(RuntimeError):
                cambiar_fotografia(self.usuario, imagen())
        self.perfil.refresh_from_db(); self.assertEqual(self.perfil.fotografia.name, anterior)
        self.assertEqual(len(list(Path(self.temp.name).rglob("*.jpg"))), 1)
