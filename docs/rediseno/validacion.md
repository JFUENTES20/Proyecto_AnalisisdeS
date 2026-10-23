# Validación de esta entrega

## Validación previa del parche (Linux)

- Python 3.12; dependencias de ejecución en `requirements.txt`.
- `manage.py check`: sin incidencias.
- Migraciones aplicadas desde una base SQLite nueva.
- `makemigrations --check --dry-run`: sin cambios pendientes.
- 33 pruebas de negocio, permisos, archivos, formularios, reportes y vistas.
- Prueba de rollback si falla un observador dentro de una aprobación.
- Límites de monto: 9999.99, 10000 y 12000.
- Correcciones conservan evaluaciones previas y exigen nueva evaluación vigente.

## Prueba previa en navegador (Linux)

Chromium headless: inicio a 1440 px y 390 px; inicio de sesión real; creación de borrador de 12000; carga de PDF; envío; revisión; evaluación; primera aprobación; bloqueo del intento de segunda aprobación con la misma cuenta; segunda aprobación con otra cuenta; panel del aspirante con avisos. Sin errores JavaScript y sin desbordamiento horizontal en las pantallas móviles revisadas.

Capturas con datos ficticios en `vistas/`: inicio, panel móvil y expediente aprobado. Son evidencia de esta ejecución local, no de un servicio publicado.

## Alcance y límites

Las pruebas locales no acreditan carga nacional, entrega push, compatibilidad completa iOS, concurrencia real PostgreSQL, ni ejecución en macOS. El workflow de GitHub utiliza PostgreSQL 16, pero sus resultados remotos se conocerán al subir la rama y ejecutar Actions.

La validación de archivos no sustituye un analizador antimalware. El administrador permite configurar identidades y comités; los expedientes no se modifican directamente allí. El registro todavía no verifica la propiedad del correo.

## Verificación en esta Mac · 21 de octubre de 2026

- Python 3.13.3, Apple Silicon arm64; entorno `.venv` independiente.
- `origin/main` actualizado y confirmado en `ac52799`; `git apply --check` pasó.
- Worktree hermano GuateBecas, rama `feature/rediseno-becanet`.
- No se encontraron instrucciones AGENTS.md en el repositorio ni en sus ancestros.
- Dependencias instaladas desde requirements.txt, incluyendo wheels macOS arm64.
- DEBUG heredado impedía iniciar: configuración explícita en `.local/demo.env`,
  clave de sesión y contraseña generadas localmente, archivo 600 excluido de Git.
- SQLite `GuateBecas/db.sqlite3` creada desde cero; sin migraciones sobre bases anteriores.
- `check`: sin incidencias; `makemigrations --check --dry-run`: sin cambios;
  `migrate --check`: sin migraciones pendientes; `test`: 33 pruebas aprobadas.
- seed_demo creó cuatro cuentas operativas y administrador.demo, más tres
  convocatorias ficticias y sus comités. Repetir conserva cuentas y contraseñas.
- Prueba HTTP contra el servidor real: login con CSRF, redirección a panel,
  expedientes y notificaciones para los cinco usuarios; administrador accede
  también a /admin/. Inicio, CSS y SVG respondieron HTTP 200.
- `git diff --check`: sin errores de whitespace. Credenciales, SQLite y entorno
  virtual confirmados como ignorados. El estado de develop conserva sus cambios.
- Identidad GuateBecas adaptada a azul/blanco/jade, texto azul oscuro y SVG propio
  inspirado en volcanes y lago de Guatemala. Se conserva aviso universitario.
- En esta Mac se verificó HTTP y se revisaron reglas responsive; no se ejecutó
  navegador automatizado ni se renovaron las capturas del diseño anterior.

La comprobación de los seis patrones y las diferencias con los anexos se encuentra
en patrones.md. No implica aceptación académica ni actualización de los diagramas.
PWA, push, correo verificado, recuperación de contraseña, PostgreSQL compartido y
AWS/HTTPS siguen pendientes. Moneda y periodicidad permanecen sin confirmar.

## Actualización responsive

La revisión posterior en Chrome de esta Mac sí ejecutó navegador automatizado.
Ver [responsive.md](responsive.md): 40 combinaciones en 360/390/768/1024/1440 px,
flujo móvil sobre SQLite temporal y capturas nuevas en vistas/responsive/.
Las capturas anteriores en vistas/ siguen siendo antecedentes del diseño inicial.

## Prueba manual confirmada por el usuario · registrada el 22 de octubre de 2026

Fuente: confirmación del usuario en esta conversación, durante la preparación de
la base para el equipo. Es una prueba manual con datos ficticios; no se atribuye
al navegador automatizado ni se inventa un identificador de expediente o dispositivo.

| Paso confirmado | Resultado observado por el usuario |
|---|---|
| Enviar una solicitud desde el teléfono | Solicitud enviada para revisión |
| Evaluar el expediente con cuenta evaluadora | Evaluación registrada |
| Dar la primera aprobación a un monto superior a 10,000 | Queda pendiente de segunda aprobación |
| Intentar la segunda aprobación con la misma persona | Operación bloqueada |
| Aprobar desde otra cuenta | Expediente aprobado |
| Consultar la cuenta del aspirante | Avisos del proceso disponibles |

Esta confirmación complementa las 33 pruebas automatizadas y la revisión responsive.
No demuestra concurrencia en PostgreSQL, entrega push ni funcionamiento productivo.
La moneda y periodicidad del umbral siguen pendientes. Se conserva esta base local
antes de organizar las tareas de los cuatro integrantes; no se han asignado roles
ni creado ramas de trabajo individuales en esta operación.

## Corrección de PostgreSQL en CI · 22 de octubre de 2026

Registro revisado: [Actions 39867869255, job pruebas](https://github.com/JFUENTES20/Proyecto_AnalisisdeS/actions/runs/39867869255/job/120134528535),
commit 29bb81c. Las 33 pruebas terminaron con dos errores:
`test_edicion_se_registra_sin_cambiar_estado` y `test_no_editar_despues_de_enviar`.
Ambos muestran `NotSupportedError: FOR UPDATE cannot be applied to the nullable
side of an outer join` al consultar en `ExpedienteFacade.editar`.

Se reprodujeron los mismos dos errores antes del arreglo en PostgreSQL 16.9 de
esta Mac. Se usó un clúster nuevo en una carpeta temporal, puerto 55439 y socket
Unix exclusivo, sin conexiones TCP, con base becanet_regresion y base temporal
test_becanet_regresion. No se usaron las bases existentes ni se cambiaron las
variables privadas del servidor de demostración. Python local: 3.13.3; CI: 3.12.15.

Corrección mínima: `select_for_update(of=("self",))` conserva el bloqueo de
Solicitud y evita bloquear el lado nullable del LEFT OUTER JOIN de convocatoria.
Se conservan select_related, transaction.atomic, permisos y validaciones.
La prueba nueva verifica que una solicitud sin convocatoria recibe ValidationError,
sin cambios de monto/estado ni evento de edición; no se filtran esos expedientes
para evitar el JOIN. El workflow conserva PostgreSQL 16 sin modificaciones.

Resultado local posterior: 34 pruebas aprobadas en PostgreSQL 16.9 y 34 en SQLite;
check sin incidencias y makemigrations --check --dry-run sin cambios en PostgreSQL.
No se afirma que Actions haya pasado: el arreglo aún no se ha subido ni ejecutado
remotamente. Esta reproducción no sustituye pruebas de concurrencia entre sesiones.

## Integración posterior con develop

La validación de integration/guatebecas-develop amplía la suite a 39 pruebas en
SQLite y PostgreSQL 16.9 y comprueba los tres escenarios de reconciliación en ambos
motores, además de transferir una copia de la base actual a destinos nuevos.
Véase [integracion.md](integracion.md) para evidencia, comandos y límites. Las
bases y los worktrees anteriores no se actualizaron ni cambiaron de rama.
