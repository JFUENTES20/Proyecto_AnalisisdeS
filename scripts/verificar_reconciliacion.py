"""Prueba tres escenarios con bases desechables; nunca usa DB_NAME existente.

Uso: .venv/bin/python scripts/verificar_reconciliacion.py --engine sqlite
     DB_HOST=/tmp/gb-pg DB_PORT=55441 DB_USER=gb_test ... --engine postgresql
PostgreSQL requiere un servidor LOCAL y un usuario con CREATEDB.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "ClaveSinteticaSoloPruebas2026!"

LEGACY_SEED = '''
import json
from pathlib import Path
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import datetime, timezone as tz
apps = MigrationExecutor(connection).loader.project_state([("usuarios", "0001_initial"), ("solicitudes", "0001_initial"), ("auth", "0012_alter_user_first_name_max_length")]).apps
User, Aspirante, Solicitud = [apps.get_model(*label) for label in [("auth", "User"), ("usuarios", "Aspirante"), ("solicitudes", "Solicitud")]]
for pk, username, email in [(7,"antiguo@example.com","duplicado@example.com"),(8,"otro","duplicado@example.com"),(9,"personal","unico@example.com")]:
    User.objects.create(pk=pk, username=username, email=email, password=make_password(os.environ["DEMO_PASSWORD"]), is_staff=pk==9, is_superuser=False, is_active=True, date_joined=timezone.now(), last_login=timezone.now())
for pk, uid in [(70,7),(80,8)]:
    a=Aspirante.objects.create(pk=pk,user_id=uid,cedula=f"EXISTENTE-{uid}",telefono=f"5555000{uid}")
    Aspirante.objects.filter(pk=pk).update(fecha_registro=datetime(2020,1,2,3,4,tzinfo=tz.utc))
for pk, email in [(301,"duplicado@example.com"),(302,"unico@example.com"),(303,"sin-cuenta@example.com")]:
    Solicitud.objects.create(pk=pk,nombre="Expediente histórico",email=email,estado="aprobada")
Path(os.environ["ORACLE"]).write_text(json.dumps({
    "users":list(User.objects.order_by("pk").values("id","username","email","password","is_staff","is_superuser","date_joined","last_login")),
    "aspirantes":list(Aspirante.objects.order_by("pk").values()),
    "solicitudes":list(Solicitud.objects.order_by("pk").values())},default=str))
'''
LEGACY_CHECK = '''
import json
from pathlib import Path
from django.contrib.auth.models import User
from django.test import Client
from usuarios.models import Aspirante, Perfil
from solicitudes.models import Solicitud
old=json.loads(Path(os.environ["ORACLE"]).read_text())
for saved in old["users"]:
    u=User.objects.get(pk=saved["id"])
    for k,v in saved.items():assert str(getattr(u,k))==str(v),(k,u.pk)
    assert u.check_password(os.environ["DEMO_PASSWORD"])
assert list(Aspirante.objects.order_by("pk").values_list("pk","user_id"))==[(70,7),(80,8)]
for saved in old["aspirantes"]:
    obj=Aspirante.objects.get(pk=saved["id"])
    for k,v in saved.items():assert str(getattr(obj,k))==str(v),(k,obj.pk)
assert set(Perfil.objects.values_list("usuario_id",flat=True))=={7,8}
assert all(p.rol=="aspirante" and p.telefono==p.usuario.aspirante.telefono for p in Perfil.objects.all())
assert not Perfil.objects.filter(usuario_id=9).exists()
for saved in old["solicitudes"]:
    obj=Solicitud.objects.get(pk=saved["id"])
    for k,v in saved.items():assert str(getattr(obj,k))==str(v),(k,obj.pk)
    assert obj.aspirante_id is None and obj.convocatoria_id is None
c=Client();assert c.login(username="antiguo@example.com",password=os.environ["DEMO_PASSWORD"])
assert c.get("/panel/").status_code==200
assert c.get("/usuarios/dashboard/",follow=True).status_code==200
'''
REDESIGN_SEED = '''
from django.core.management import call_command
from django.contrib.auth.models import User, Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal
from convocatorias.models import Convocatoria
from solicitudes.services import ExpedienteFacade as F
from solicitudes.models import Notificacion
from django.contrib.admin.models import LogEntry, ADDITION
from django.contrib.contenttypes.models import ContentType
call_command("seed_demo",verbosity=0)
ana=User.objects.get(username="aspirante.demo")
evaluador=User.objects.get(username="evaluador.demo")
primero=User.objects.get(username="aprobador.uno");segundo=User.objects.get(username="aprobador.dos")
# Permisos existentes se transfieren por identidad natural, no por ID de Permission.
g=Group.objects.create(name="Grupo existente")
g.permissions.add(Permission.objects.get(codename="view_solicitud",content_type__app_label="solicitudes"))
ana.groups.add(g);ana.user_permissions.add(Permission.objects.get(codename="view_convocatoria",content_type__app_label="convocatorias"))
s=F.crear(ana,Convocatoria.objects.order_by("pk").first(),Decimal("12000"),"Motivación de datos sintéticos para la reconciliación.")
F.adjuntar(ana,s.pk,"Documento ficticio",SimpleUploadedFile("constancia.pdf",b"%PDF-1.4\\nDatos ficticios\\n%%EOF",content_type="application/pdf"))
F.transicionar(ana,s.pk,"enviar");F.transicionar(evaluador,s.pk,"revisar","Revisión de prueba.")
F.evaluar(evaluador,s.pk,90,"Evaluación independiente de prueba.")
F.transicionar(primero,s.pk,"aprobar","Primera decisión de prueba.");F.transicionar(segundo,s.pk,"aprobar","Segunda decisión de prueba.")
Notificacion.objects.filter(destinatario=ana).update(leida=True)
LogEntry.objects.log_actions(user_id=User.objects.get(username="administrador.demo").pk,queryset=Convocatoria.objects.filter(pk=s.convocatoria_id),action_flag=ADDITION,change_message="Configuración ficticia previa")
'''
REDESIGN_CHECK = '''
from django.contrib.auth.models import User,Group
from django.test import Client
from usuarios.models import Aspirante,Perfil
from solicitudes.models import Solicitud,Documento,Decision,EventoAuditoria,Notificacion
from evaluaciones.models import Evaluacion,Comite
from django.contrib.admin.models import LogEntry
from django.core.files.storage import default_storage
assert not Aspirante.objects.exists() # No se inventan cédulas ni identidades históricas.
assert Perfil.objects.count()==5 and User.objects.count()==5
assert User.objects.filter(is_superuser=True).count()==1
for u in User.objects.all():assert u.check_password(os.environ["DEMO_PASSWORD"])
s=Solicitud.objects.get();assert s.estado=="aprobada" and s.monto==12000
assert s.aspirante.username=="aspirante.demo" and s.convocatoria is not None
assert Decision.objects.filter(solicitud=s,accion="aprobar").count()==2
assert Evaluacion.objects.get(solicitud=s).evaluador.username=="evaluador.demo"
assert Comite.objects.filter(miembros=User.objects.get(username="evaluador.demo")).count()==3
assert EventoAuditoria.objects.filter(solicitud=s).count()==7
assert Notificacion.objects.filter(destinatario=s.aspirante,leida=True).exists()
assert Group.objects.get(name="Grupo existente").permissions.get().codename=="view_solicitud"
assert s.aspirante.user_permissions.get().codename=="view_convocatoria"
assert LogEntry.objects.count()==1 and LogEntry.objects.get().content_type.model=="convocatoria"
d=Documento.objects.get(solicitud=s)
with default_storage.open(d.archivo.name,"rb") as f:assert f.read().startswith(b"%PDF-1.4")
c=Client();assert c.login(username="aspirante.demo",password=os.environ["DEMO_PASSWORD"])
assert c.get(f"/solicitudes/{s.pk}/").status_code==200
assert c.get(f"/documentos/{d.pk}/").status_code==200
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=["sqlite", "postgresql"], default="sqlite")
    args = parser.parse_args()
    prefix = "gbverify_" + uuid.uuid4().hex[:12]
    pg = None
    created = []
    with tempfile.TemporaryDirectory(prefix="guatebecas-reconciliacion-") as temp:
        temp = Path(temp)
        settings_file = temp / "gb_verification_settings.py"
        settings_file.write_text('''from becas_platform.settings import *
import json, os
DATABASES=json.loads(os.environ["GBI_DATABASES"])
MEDIA_ROOT=os.environ["GBI_MEDIA"]
SECRET_KEY="solo-tests-aislados"
DEBUG=True
ALLOWED_HOSTS=["testserver","localhost","127.0.0.1"]
if os.getenv("GBI_SCHEMA")=="redesign":
    MIGRATION_MODULES={"usuarios":"usuarios.fixtures_redisenio"}
''')
        env = os.environ.copy()
        env.update(DEBUG="true", DJANGO_SETTINGS_MODULE="gb_verification_settings", PYTHONPATH=str(temp)+os.pathsep+str(ROOT), DEMO_PASSWORD=PASSWORD, ORACLE=str(temp / "oracle.json"))
        if args.engine == "postgresql":
            import psycopg
            from psycopg import sql
            host = os.getenv("DB_HOST", "localhost")
            if host not in ("localhost", "127.0.0.1", "::1") and not host.startswith(("/tmp/", "/private/tmp/")):
                raise SystemExit("Solo se permiten servidores PostgreSQL locales para estas pruebas.")
            pg = psycopg.connect(dbname="postgres", host=host, port=os.getenv("DB_PORT", "5432"), user=os.environ["DB_USER"], password=os.getenv("DB_PASSWORD", ""), autocommit=True)
        def database(label):
            name = prefix + "_" + label
            if pg:
                with pg.cursor() as cursor:cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
                created.append(name)
                return {"ENGINE":"django.db.backends.postgresql","NAME":name,"HOST":host,"PORT":os.getenv("DB_PORT","5432"),"USER":os.environ["DB_USER"],"PASSWORD":os.getenv("DB_PASSWORD","")}
            return {"ENGINE":"django.db.backends.sqlite3","NAME":str(temp / (name+".sqlite3"))}
        def run(db, *command, schema="integrated", source=None, media=None, ok=True):
            child = env | {"GBI_DATABASES":json.dumps({"default":db, **({"redesign_copy":source} if source else {})}),"GBI_SCHEMA":schema,"GBI_MEDIA":str(media or temp / "media")}
            result = subprocess.run([sys.executable,str(ROOT/"manage.py"),*command],cwd=ROOT,env=child,text=True,capture_output=True)
            if (result.returncode == 0) != ok:
                raise RuntimeError("Comando fallido: "+" ".join(command[:3])+"\n"+result.stdout+result.stderr)
            return result.stdout if ok else result.stderr
        def shell(db, code, **kw):
            return run(db,"shell","-c","import os\n"+code,**kw)
        try:
            fresh = database("fresh")
            run(fresh,"migrate","--noinput","--verbosity=0")
            shell(fresh,'''from django.contrib.auth.models import User
from usuarios.models import Aspirante,Perfil
from django.test import Client
assert not User.objects.exists() and not Aspirante.objects.exists() and not Perfil.objects.exists()
c=Client();r=c.post("/registro/",{"username":"nueva","first_name":"Nueva","last_name":"Cuenta","email":"nueva@example.com","password1":os.environ["DEMO_PASSWORD"],"password2":os.environ["DEMO_PASSWORD"]})
assert r.status_code==302 and r.url=="/panel/"
u=User.objects.get(username="nueva");assert u.check_password(os.environ["DEMO_PASSWORD"])
assert u.perfil.rol=="aspirante" and not u.is_staff and not u.is_superuser and not Aspirante.objects.exists()
''')
            print(args.engine+": instalación desde cero OK",flush=True)
            legacy = database("legacy")
            run(legacy,"migrate","auth","--noinput","--verbosity=0")
            run(legacy,"migrate","admin","--noinput","--verbosity=0")
            run(legacy,"migrate","sessions","--noinput","--verbosity=0")
            run(legacy,"migrate","usuarios","0001","--noinput","--verbosity=0")
            run(legacy,"migrate","solicitudes","0001","--noinput","--verbosity=0")
            shell(legacy,LEGACY_SEED)
            run(legacy,"migrate","--noinput","--verbosity=0")
            shell(legacy,LEGACY_CHECK)
            pending = json.loads(run(legacy,"revisar_vinculos_legado"))
            assert pending == [{"solicitud":301,"candidatos":[7,8],"revision":"ambigua"},{"solicitud":302,"candidatos":[9],"revision":"manual"},{"solicitud":303,"candidatos":[],"revision":"manual"}],pending
            print(args.engine+": actualización develop, identidades, contraseñas, fechas y correos ambiguos OK",flush=True)
            source, target = database("redesign"), database("transfer")
            source_media, target_media = temp/"source_media",temp/"target_media"
            run(source,"migrate","--noinput","--verbosity=0",schema="redesign",media=source_media)
            shell(source,REDESIGN_SEED,schema="redesign",media=source_media)
            run(target,"migrate","--noinput","--verbosity=0",media=target_media)
            transfer = ["transferir_redisenio","--source","redesign_copy","--media-source",str(source_media),"--confirm-source-copy"]
            # Negative preflight: missing source files must not import any rows.
            doc = next(source_media.rglob("*.pdf"));original = doc.read_bytes();doc.unlink()
            assert "Documento ausente" in run(target,*transfer,source=source,media=target_media,ok=False)
            shell(target,"from django.contrib.auth.models import User\nassert not User.objects.exists()",media=target_media)
            doc.write_bytes(original)
            # A storage failure after inserting the records must roll back all DB rows.
            rollback = (
                "from unittest.mock import patch\n"
                "from django.core.management import call_command\n"
                "from django.contrib.auth.models import User\n"
                "from usuarios.models import Perfil\n"
                "from solicitudes.models import Solicitud\n"
                "try:\n"
                " with patch('usuarios.management.commands.transferir_redisenio.default_storage.save', side_effect=OSError('fallo de almacenamiento simulado')):\n"
                f"  call_command('transferir_redisenio', source='redesign_copy', media_source={str(source_media)!r}, confirm_source_copy=True)\n"
                "except OSError as error:\n"
                " assert 'simulado' in str(error)\n"
                "else: raise AssertionError('Se esperaba fallo de almacenamiento')\n"
                "assert not User.objects.exists() and not Perfil.objects.exists() and not Solicitud.objects.exists()\n"
            )
            shell(target,rollback,source=source,media=target_media)
            print(run(target,*transfer,source=source,media=target_media).strip(),flush=True)
            shell(target,REDESIGN_CHECK,media=target_media)
            # Repeating import cannot overwrite a populated destination.
            assert "destino debe estar vacío" in run(target,*transfer,source=source,media=target_media,ok=False)
            shell(target,REDESIGN_CHECK,media=target_media)
            # Imported explicit PKs must not collide with subsequent inserts.
            shell(target, """from django.contrib.auth.models import User
from django.db import transaction
ultimo=max(User.objects.values_list("pk",flat=True))
with transaction.atomic():
    nuevo=User.objects.create(username="prueba_secuencia_sin_persistir")
    assert nuevo.pk>ultimo
    transaction.set_rollback(True)
""", media=target_media)
            shell(source,REDESIGN_CHECK.replace('assert not Aspirante.objects.exists()', 'assert "usuarios_aspirante" not in __import__("django.db",fromlist=["connection"]).connection.introspection.table_names()'),schema="redesign",media=source_media)
            print(args.engine+": transferencia rediseño, archivos, permisos, relaciones y rechazos preventivos OK",flush=True)
        finally:
            if pg:
                for name in reversed(created):
                    with pg.cursor() as cursor:cursor.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
                pg.close()


if __name__ == "__main__":
    main()
