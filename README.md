# GuateBecas · Plataforma de gestión de becas

Proyecto universitario de Análisis de Sistemas II, Universidad Mariano Gálvez.
Esta rama integra el rediseño con `develop`, conservando ambos historiales, los documentos y las migraciones iniciales publicadas de usuarios y solicitudes. No representa un sistema oficial del Gobierno.

## Estado de esta entrega

Primera versión local del rediseño: convocatorias públicas; registro de aspirantes; acceso por rol; solicitudes en borrador; carga y descarga autorizada de documentos; revisión por comité; evaluación; correcciones; aprobación simple y doble; seguimiento; avisos internos; auditoría y exportación CSV.

El personal configura convocatorias, comités y perfiles desde `/admin/`. Las decisiones sobre expedientes se realizan desde el portal para que pasen por los servicios de negocio, nunca editando el estado en el administrador.

**Pendiente:** verificación de correo, Web Push, instalación como PWA y pruebas de concurrencia/carga. El usuario reportó un despliegue base AWS/HTTPS; su actualización con recuperación y su respaldo/restauración siguen pendientes de verificación. No cargar documentos personales reales ni publicar esta versión como un servicio gubernamental. Los campos monetarios no muestran moneda hasta confirmar su unidad y periodicidad con el Product Owner.

## Recuperación de contraseña

La rama incluye recuperación Django con cola, controles por IP/correo y backend
SMTP publicado con CA configurable y validación TLS. El usuario confirmó solicitud,
recepción en Gmail, cambio de contraseña y acceso desde una vista local independiente.
Esa validación no equivale a haber desplegado este incremento en AWS.

Configuración, límites y evidencia: [recuperacion-correo.md](docs/rediseno/recuperacion-correo.md).
Plan AWS, respaldo, supervisión y reversión (sin ejecutar):
[recuperacion-aws.md](docs/despliegue/recuperacion-aws.md).

## Equipo

Jose Fuentes · Pablo Maldonado · Flor Escobar · Elena Ovalle · Karen Canuc.

## Ejecutar en macOS (incluido Apple Silicon)

Necesitas Python 3.13 y Git. Los comandos se ejecutan dentro de la carpeta del proyecto. Validado en esta Mac con Python 3.13.3, Django 5.2.18 y SQLite; 110 pruebas aprobadas en SQLite y PostgreSQL 16.9 en el incremento actual de recuperación.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export DEBUG=true
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

GitHub Actions ejecuta la matriz SQLite/PostgreSQL 16 con comprobaciones de reconciliación. Los resultados corresponden a cada commit: consultar la ejecución del candidato en GitHub antes de entregar. SQLite no verifica el bloqueo de filas de PostgreSQL: antes del despliegue se deben probar solicitudes simultáneas contra PostgreSQL.

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

Rama local: `integration/guatebecas-develop`, basada en `origin/develop` (`5670e2b`)
e incorporando `origin/feature/rediseno-becanet` (`55b90dd`) mediante merge.
Se conserva `usuarios.0001` (Aspirante); Perfil se añade en 0002 y se copia la
relación histórica en 0003, sin fabricar cédulas ni modificar contraseñas o privilegios.
Los expedientes sin propietario quedan para revisión manual, nunca se asignan por correo.

**No aplicar esta rama directamente a una base del rediseño previo:** su 0001 de
usuarios es distinta. La transferencia soportada va de una copia independiente a
una base nueva y almacenamiento separado. No se utiliza --fake. Los cambios locales
sin publicar de develop permanecen fuera de esta integración.

Instrucciones, compatibilidad de rutas, herramientas de transferencia y resultados:
[docs/rediseno/integracion.md](docs/rediseno/integracion.md).

```bash
.venv/bin/python scripts/verificar_reconciliacion.py --engine sqlite
# PostgreSQL necesita un servidor local de pruebas y usuario con CREATEDB:
DB_HOST=/tmp/gb-integration-pg DB_PORT=55441 DB_USER=gb_test \
  .venv/bin/python scripts/verificar_reconciliacion.py --engine postgresql
```

Ambos comandos crean destinos desechables. El [PR de integración #6](https://github.com/JFUENTES20/Proyecto_AnalisisdeS/pull/6) conserva el historial de la integración; las mejoras posteriores se revisan mediante PR encadenados. Esta rama de recuperación tiene como base feature/foto-perfil.

## Antes de publicar

Configurar `DEBUG=false`, `SECRET_KEY` aleatoria, `ALLOWED_HOSTS` exactos y PostgreSQL; preparar servidor WSGI, archivos estáticos, HTTPS y copias de seguridad; verificar correo y procesos de registro; limitar intentos de acceso y cargas; añadir análisis antimalware; usar almacenamiento privado y acceso autenticado. No se incluye aún una configuración de despliegue lista para AWS. El bloqueo pesimista y las restricciones de base de datos deben verificarse en PostgreSQL antes de uso compartido.

## Worktrees y demostración existente en esta Mac

- `../Proyecto_AnalisisdeS`: develop con cambios locales conservados.
- `../GuateBecas`: rediseño y servidor de demostración existente, intactos.
- `../GuateBecas-integracion`: integración y entorno virtual independientes;
  no se inicia otro servidor ni se copian configuraciones privadas aquí.

La configuración, contraseña, SQLite y archivos de demostración siguen excluidos
de Git. No se modificó el servidor activo ni se cambió su base a la integración.
Las capturas previas son antecedentes del rediseño, conservados para el equipo.
La ilustración SVG de volcanes es original del proyecto y se mantiene la identidad
GuateBecas azul/blanco/jade y el aviso de demostración universitaria.
