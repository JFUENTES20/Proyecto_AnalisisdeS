# GuateBecas · Plataforma de gestión de becas

Proyecto universitario de Análisis de Sistemas II, Universidad Mariano Gálvez.
Esta rama reconstruye la base funcional conservando el historial de `main`, sus documentos y la migración inicial de solicitudes. No representa un sistema oficial del Gobierno.

## Estado de esta entrega

Primera versión local del rediseño: convocatorias públicas; registro de aspirantes; acceso por rol; solicitudes en borrador; carga y descarga autorizada de documentos; revisión por comité; evaluación; correcciones; aprobación simple y doble; seguimiento; avisos internos; auditoría y exportación CSV.

El personal configura convocatorias, comités y perfiles desde `/admin/`. Las decisiones sobre expedientes se realizan desde el portal para que pasen por los servicios de negocio, nunca editando el estado en el administrador.

**Pendiente:** verificación de correo, recuperación de contraseña, Web Push, instalación como PWA, HTTPS, alojamiento AWS y pruebas de concurrencia/carga. No cargar documentos personales reales ni publicar esta versión como un servicio gubernamental. Los campos monetarios no muestran moneda hasta confirmar su unidad y periodicidad con el Product Owner.

## Equipo

Jose Fuentes · Pablo Maldonado · Flor Escobar · Elena Ovalle · Karen Canuc.

## Ejecutar en macOS (incluido Apple Silicon)

Necesitas Python 3.13 y Git. Los comandos se ejecutan dentro de la carpeta del proyecto. Validado en esta Mac con Python 3.13.3, Django 5.2.18 y SQLite; 33 pruebas aprobadas.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abre `http://127.0.0.1:8000/`. La configuración predeterminada usa SQLite para probar sin instalar PostgreSQL. Las claves y las bases de datos locales no se suben a Git.

### Datos ficticios para una demostración

En otra terminal, activa el mismo entorno virtual. Elige una contraseña local de al menos 12 caracteres:

```bash
export DEMO_PASSWORD='EligeUnaClaveLocalLarga2026!'
python manage.py seed_demo
unset DEMO_PASSWORD
```

Cuentas creadas: `administrador.demo` (superusuario solo de demostración), `aspirante.demo`, `evaluador.demo`, `aprobador.uno` y `aprobador.dos`. Todas usan la clave que elegiste. Repetir el comando conserva las cuentas existentes y no cambia sus claves. Las convocatorias ficticias abren con fechas relativas al momento de su creación.

Para probar: inicia sesión como aspirante, crea un borrador para la convocatoria universitaria con monto 12000, adjunta un PDF y envíalo. Cierra sesión; como evaluador inicia la revisión y registra el puntaje. Como primer aprobador aprueba; el expediente debe quedar pendiente de segunda aprobación. Como segundo aprobador aprueba; el expediente debe quedar aprobado. Consulta los avisos del aspirante y el historial del personal.

### PostgreSQL

Crea una base y un usuario propios para el proyecto. Exporta las variables; `.env.example` es una plantilla y NO se carga automáticamente:

```bash
export DB_ENGINE=postgresql
export DB_NAME=becanet
export DB_USER=becanet
export DB_PASSWORD='tu-clave-local'
export DB_HOST=localhost
export DB_PORT=5432
python manage.py migrate
python manage.py test
```

La base PostgreSQL es independiente de SQLite: cambiar de motor no copia los datos. El usuario de pruebas necesita permiso para crear la base temporal de tests.

## Calidad

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

GitHub Actions está configurado para ejecutar estas comprobaciones con PostgreSQL 16 cuando esta rama sea subida. Su ejecución remota aún no se ha verificado. SQLite no verifica el bloqueo de filas de PostgreSQL: antes del despliegue se deben probar solicitudes simultáneas contra PostgreSQL.

## Organización

- `usuarios`: perfiles, registro, identidad y roles.
- `convocatorias`: programas, fechas y montos máximos.
- `solicitudes`: expediente, documentos, decisiones, estados, auditoría y avisos.
- `evaluaciones`: comités y evaluaciones vigentes/históricas.
- `solicitudes/services.py`: operaciones atómicas de negocio.
- `solicitudes/patterns.py`: State y Observer.
- `solicitudes/reportes.py`: Builder y Factory Method.
- `solicitudes/storage.py`: Adapter para almacenamiento privado.
- `templates` y `static`: interfaz responsive sin dependencias CDN.

Ver `docs/rediseno/arquitectura.md`, `patrones.md`, `backlog.md` y `validacion.md`.

## Integración con el repositorio del grupo

La rama de trabajo es `feature/rediseno-becanet`, basada en `main` (`ac52799`). Los commits anteriores no se reescriben. Hay cambios en `develop` que no están en `main`; revisar su registro de aspirantes antes de integrar, especialmente su migración de `usuarios`, que difiere de esta rama.

El parche de entrega se aplica desde un clon limpio basado en ese `main`:

```bash
git fetch origin
git switch -c feature/rediseno-becanet origin/main
git apply --check /ruta/al/BecaNet-redesign.patch
git apply /ruta/al/BecaNet-redesign.patch
```

Si el chequeo falla porque `main` avanzó, no forzar: revisar las diferencias. Si hay modificaciones locales, conservarlas antes de cambiar de rama. Ejecutar las pruebas y revisar `git diff`. Luego crear commits descriptivos de los cambios reales y subir la rama para un pull request revisado por otro integrante.

No borrar bases existentes. Las migraciones preservan solicitudes antiguas de `main` como expedientes sin propietario/convocatoria; su vinculación exige una revisión manual de identidad. Una base ya migrada con el esquema distinto de `develop` necesita un plan de reconciliación antes de aplicar esta rama.

## Antes de publicar

Configurar `DEBUG=false`, `SECRET_KEY` aleatoria, `ALLOWED_HOSTS` exactos y PostgreSQL; preparar servidor WSGI, archivos estáticos, HTTPS y copias de seguridad; verificar correo y procesos de registro; limitar intentos de acceso y cargas; añadir análisis antimalware; usar almacenamiento privado y acceso autenticado. No se incluye aún una configuración de despliegue lista para AWS. El bloqueo pesimista y las restricciones de base de datos deben verificarse en PostgreSQL antes de uso compartido.

## Demostración local en esta Mac

Worktree: `../GuateBecas`, rama `feature/rediseno-becanet`, base `ac52799`.
No se modificaron las bases ni los archivos pendientes de `develop`.

La instalación local ya tiene `.venv`, una SQLite nueva `db.sqlite3` y datos ficticios.
La configuración y contraseña generadas están en `.local/demo.env` (permisos 600,
excluido de Git). `iniciar-local.sh` carga ese archivo explícitamente; no depende
del valor de DEBUG heredado de la terminal. No compartir ni versionar ese archivo.

```bash
cd ../GuateBecas
./iniciar-local.sh
# http://127.0.0.1:8000/ ; acceso por usuario en /acceso/
# Ver la contraseña local de las cuentas ficticias:
sed -n 's/^export DEMO_PASSWORD=//p' .local/demo.env
```

Roles: `aspirante.demo`, `evaluador.demo`, `aprobador.uno`, `aprobador.dos` y
`administrador.demo` (también puede entrar en `/admin/`). Usan la misma contraseña
local de demostración. El administrador es solo para esta base ficticia.

Para repetir comprobaciones: `./iniciar-local.sh check`,
`./iniciar-local.sh makemigrations --check --dry-run`, `./iniciar-local.sh test`.
Para ver migraciones sin aplicar: `./iniciar-local.sh migrate --check`.

Identidad provisional GuateBecas: azul/blanco, texto azul oscuro y acento jade.
`static/img/volcanes-guatemala.svg` es una ilustración vectorial original creada
para el proyecto; no incorpora imágenes de terceros ni emblemas oficiales.
Las capturas previas de `docs/rediseno/vistas/` corresponden al diseño anterior.
