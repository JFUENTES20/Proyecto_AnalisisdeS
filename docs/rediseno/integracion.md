# Integración de GuateBecas y develop

Estado: integración local comprobada, pendiente de revisión del equipo y publicación.
Fecha de validación: 22 de octubre de 2026. No se cambiaron los worktrees originales,
sus configuraciones privadas ni el servidor en uso. No se conectó a bases externas.

## Rama e historial

Worktree: `../GuateBecas-integracion`, rama `integration/guatebecas-develop`.
Base publicada: `origin/develop` en `5670e2b`.
Rediseño incorporado: `origin/feature/rediseno-becanet` en `55b90dd`.
Merge local `f104207`: conserva ambos commits como padres, sin squash ni rebase.
PR previsto, todavía NO creado: `integration/guatebecas-develop` → `develop`.

Se resolvieron conflictos de URLs, Observer/State, detalle de expediente y módulo
usuarios. Se conserva el flujo del rediseño y se recupera el modelo histórico.
Las plantillas antiguas de usuarios se retiran para evitar referencias a formularios
y vistas incompatibles: sus rutas funcionan mediante compatibilidad explícita.
Los documentos de integrantes y los cuatro diagramas se conservaron byte a byte.
Las diferencias entre diagramas y arquitectura siguen documentadas en patrones.md;
esta integración no significa aprobación de todas las decisiones por el equipo.

## Historial canónico y actualización desde develop

1. `usuarios/0001_initial.py` es idéntica a la publicada en develop; crea Aspirante.
2. `0002_perfil` añade Perfil. No cambia ni renombra la tabla histórica.
3. `0003_copiar_perfiles_legacy` crea un perfil aspirante por cada Aspirante existente,
   enlazándolo por `user_id` y copiando el teléfono. Conserva Aspirante, su PK,
   cédula, fecha de registro y teléfono. No cambia User, hashes, grupos ni flags.
   Una cuenta sin Aspirante no recibe una cédula ni un registro Aspirante artificial.
4. El registro nuevo crea User + Perfil, con usuario explícito. Las cuentas antiguas
   que usan un correo como username conservan ese username y su acceso.
5. La migración inicial de solicitudes también permanece como estaba publicada;
   los campos nuevos se añaden mediante la 0002 existente del rediseño.

Las solicitudes antiguas conservan PK, nombre, correo, estado y fechas. Sus campos
nuevos de propietario y convocatoria quedan nulos; no se deduce identidad por correo.
`manage.py revisar_vinculos_legado` produce un informe sin modificar datos: distingue
correos ambiguos y candidatos únicos o inexistentes. Todos necesitan revisión manual,
incluidos los de coincidencia única. No se fabrican evaluaciones, decisiones ni avisos
históricos. Los expedientes sin propietario no aparecen en el portal de un aspirante.

La actualización debe ensayarse sobre una copia de la base publicada, con sus claves
y archivos respaldados, antes de decidir un cambio de base compartida. El esquema
local sin publicar del worktree develop NO es el esquema de origin/develop: su
Solicitud enlaza Aspirante y requiere un plan separado si ya se aplicó a alguna base.
No se ensayó ese esquema local ni se conectó con Cloud SQL para inspeccionarlo.

## Transferencia desde el rediseño previo

La 0001 del rediseño crea Perfil y está registrada con el mismo nombre que la de
Aspirante. No se ejecuta migrate directamente contra esa base con el código integrado.
Tampoco se cambia django_migrations ni se utiliza --fake.

Procedimiento soportado: COPIA independiente del origen → base integrada NUEVA y
vacía + almacenamiento destino independiente. El comando `transferir_redisenio`:

- Exige dos alias, confirmación de copia, esquema de origen Perfil sin Aspirante y
  destino con el historial integrado. Rechaza datos de negocio preexistentes.
- Conserva PK, usernames, hashes, flags y roles ya existentes. Grupos y permisos se
  resuelven por claves naturales; no se inventan permisos para sortear conflictos.
- Transfiere Perfil, convocatorias, comités/miembros, solicitudes, documentos,
  evaluaciones, decisiones, auditoría, avisos y entradas del administrador.
- Copia los archivos referenciados conservando su ruta y verifica SHA-256.
- Comprueba una representación completa de los registros antes de confirmar la
  transacción y reinicia las secuencias de PostgreSQL tras importar PK explícitas.
- Ante una excepción revierte filas y elimina los archivos recién copiados.
- No transfiere sesiones ni contenido de django_migrations, ContentType o Permission
  por sus IDs de origen. Las sesiones del servidor original siguen intactas.

Ejemplo de configuración PRIVADA, después de preparar una copia coherente de la
SQLite y sus documentos en `.local/copia-redisenio.sqlite3` y `.local/media-copia/`:

```python
# .local/integracion_local.py; NO versionar ni apuntar al origen activo.
from becas_platform.settings import *
DEBUG = True
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / ".local/integrada.sqlite3",  # nueva y vacía
    },
    "redesign_copy": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": (BASE_DIR / ".local/copia-redisenio.sqlite3").as_uri() + "?mode=ro",
        "OPTIONS": {"uri": True},
    },
}
MEDIA_ROOT = BASE_DIR / ".local/media-integrada"
```

```bash
export PYTHONPATH="$PWD/.local:$PWD"
export DJANGO_SETTINGS_MODULE=integracion_local
export DEBUG=true
.venv/bin/python manage.py migrate
.venv/bin/python manage.py transferir_redisenio --source redesign_copy \
  --media-source "$PWD/.local/media-copia" --confirm-source-copy
```

La herramienta no fusiona dos bases pobladas ni resuelve colisiones de identidades
entre ellas. Si hay permisos personalizados o ContentTypes ajenos al código actual,
la importación requiere revisar sus definiciones; no se debe omitir la verificación.
La transferencia es para una copia estable/offline: ante interrupción del proceso o
desajuste entre snapshot y archivos se descarta/recrea el destino y se repite desde
la copia. No es una sincronización continua ni una transacción distribuida.

## Rutas compatibles

| Ruta antigua | Comportamiento |
|---|---|
| GET `/usuarios/registro/` | 302 a `/registro/` |
| POST `/usuarios/registro/` | 307 conserva método/cuerpo; valida el formulario nuevo |
| GET `/usuarios/login/` | 302 a `/acceso/`; conserva next, validado por Django |
| GET `/usuarios/dashboard/` | 302 a `/panel/`; aplica autenticación y permisos actuales |
| GET `/usuarios/logout/` | Confirmación, mantiene la sesión |
| POST `/usuarios/logout/` | Cierre con CSRF, igual al flujo moderno |

El formulario publicado antiguo ya no se renderiza. Un POST antiguo con nombres de
campos anteriores muestra la validación del formulario actual, sin crear cuentas
incompletas ni fabricar un username. El acceso sigue siendo por usuario, no una
búsqueda nueva por correo. Se mantiene el rechazo de redirecciones next externas.

## Verificación reproducible y resultados

Python 3.13.3 y PostgreSQL 16.9 locales, entorno virtual propio de este worktree.

| Prueba | SQLite | PostgreSQL 16.9 |
|---|---|---|
| Suite de aplicación | 39/39 | 39/39 |
| Instalación desde cero + registro sin cédula ficticia | OK | OK |
| Actualización de esquema publicado develop | OK | OK |
| Transferencia desde esquema previo del rediseño | OK | OK |
| Rechazo de origen sin archivo y de destino ocupado | OK | OK |
| Rollback de filas ante fallo de almacenamiento simulado | OK | OK |
| Inserción posterior sin colisión de PK importadas | OK | OK |
| check / makemigrations --check --dry-run | OK | OK |

La actualización ensaya cuentas con correo duplicado, username correo, hashes y
privilegios existentes, identidades con PK distintas de User y fecha de registro
histórica, además de expedientes sin dueño. Verifica que nada se asigna por correo.
El escenario del rediseño preserva 37 registros, un PDF, membresías, permisos,
una evaluación, ambas aprobaciones por personas distintas, auditoría y avisos.

También se hizo backup por conexión SQLite de solo lectura de la base ACTUAL del
worktree GuateBecas y copia de sus documentos a una carpeta temporal privada:
transferencia verificada a SQLite y PostgreSQL nuevos de **35 registros y un archivo**.
La copia de origen mantuvo su SHA-256. No se transfirió sobre ninguna base existente.

```bash
# No usa la DB_NAME existente: crea y elimina sus propias bases desechables.
.venv/bin/python scripts/verificar_reconciliacion.py --engine sqlite
# Servidor PostgreSQL local separado; requiere CREATEDB, nunca un host externo.
DB_HOST=/tmp/gb-integration-pg DB_PORT=55441 DB_USER=gb_test \
  .venv/bin/python scripts/verificar_reconciliacion.py --engine postgresql
```

Los escenarios SQLite viven en TemporaryDirectory; PostgreSQL usa bases con prefijo
aleatorio gbverify_ dentro de un clúster temporal propio, accesible solo por socket.
La suite usa su base de tests habitual; en esta validación también fue independiente.
La matriz de GitHub Actions queda configurada para ambos motores y los tres
escenarios, pero su ejecución remota está pendiente porque esta rama no se ha subido.

## Decisiones y límites pendientes

- Revisar y asignar manualmente solicitudes antiguas sin identidad/convocatoria.
- Definir si las cuentas nuevas deben aportar cédula y cómo actualizar teléfono
  después de la copia inicial entre Perfil y el registro histórico Aspirante.
- Revisar por separado cualquier base que haya usado las migraciones locales sin publicar.
- No se ha probado concurrencia entre procesos, carga, Safari/dispositivos físicos
  adicionales ni una migración de una base externa real. No se ejecutaron downgrades;
  conservar copias y restaurarlas en vez de revertir migraciones con datos.
- Moneda/periodicidad, PWA, push, verificación/recuperación de correo, PostgreSQL
  compartido y AWS/HTTPS siguen pendientes. El equipo debe revisar la integración.
