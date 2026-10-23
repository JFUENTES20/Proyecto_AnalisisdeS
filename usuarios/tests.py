from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from .models import Aspirante, Perfil


class CompatibilidadTests(TestCase):
    def test_usuario_antiguo_con_correo_como_username_conserva_acceso(self):
        usuario = User.objects.create_user(username="antiguo@example.com", password="ClaveSoloTest123!")
        Perfil.objects.create(usuario=usuario)
        original = usuario.password
        response = self.client.post("/acceso/", {"username": usuario.username, "password": "ClaveSoloTest123!"})
        self.assertRedirects(response, "/panel/")
        usuario.refresh_from_db()
        self.assertEqual(usuario.password, original)
        self.assertEqual(usuario.username, "antiguo@example.com")

    def test_rutas_antiguas_redirigen_a_las_vistas_nuevas(self):
        for old, new in [("registro", "/registro/"), ("login", "/acceso/"), ("dashboard", "/panel/")]:
            response = self.client.get(f"/usuarios/{old}/")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, new)

    def test_post_registro_antiguo_conserva_metodo_y_datos(self):
        data = {"username": "nueva", "first_name": "Nueva", "last_name": "Cuenta",
                "email": "nueva@example.com", "password1": "ClaveSoloTest123!", "password2": "ClaveSoloTest123!"}
        response = self.client.post("/usuarios/registro/", data)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.url, "/registro/")
        response = self.client.post("/usuarios/registro/", data, follow=True)
        self.assertEqual(response.status_code, 200)
        usuario = User.objects.get(username="nueva")
        self.assertTrue(usuario.check_password(data["password1"]))
        self.assertEqual(usuario.perfil.rol, "aspirante")
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        self.assertFalse(Aspirante.objects.filter(user=usuario).exists())

    def test_logout_antiguo_get_no_cierra_y_post_exige_csrf(self):
        usuario = User.objects.create_user(username="demo", password="ClaveSoloTest123!")
        client = Client(enforce_csrf_checks=True)
        client.force_login(usuario)
        response = client.get("/usuarios/logout/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("_auth_user_id", client.session)
        self.assertEqual(client.post("/usuarios/logout/").status_code, 403)
        response = client.post("/usuarios/logout/", {"csrfmiddlewaretoken": client.cookies["csrftoken"].value})
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", client.session)

    def test_next_no_permite_redireccion_a_sitio_ajeno(self):
        usuario = User.objects.create_user(username="demo", password="ClaveSoloTest123!")
        Perfil.objects.create(usuario=usuario)
        response = self.client.post("/acceso/?next=https://ajeno.example/", {"username": "demo", "password": "ClaveSoloTest123!"})
        self.assertEqual(response.url, "/panel/")
