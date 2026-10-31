# Revisión funcional de cierre

Base: `92ccf264830d665137408e6951e5fa0d663c72de`, el commit desplegado que indicó
el usuario. Rama local `fix/cierre-funcional`, worktree `GuateBecas-funcional`.
Esta corrección no se ha desplegado. El informe no acredita revisión
humana, aceptación del equipo ni pruebas nuevas sobre AWS.

## Resultado por control

| Control | Comportamiento comprobado y evidencia |
| --- | --- |
| Documentación antes de enviar | `ExpedienteFacade.transicionar` exige que exista al menos una fila de Documento vinculada y que la convocatoria esté abierta. `test_no_enviar_sin_documentos` comprueba el rechazo sin documentos. No hay tipos documentales obligatorios configurados por convocatoria. |
| Propiedad del expediente | `visibles` limita listados del aspirante a su cuenta. Detalle y descarga pasan por `puede_ver`, después de autenticación. `test_solicitud_ajena_no_es_visible` y `test_no_descargar_documento_ajeno` verifican los rechazos; `test_carga_y_descarga_autorizada` comprueba la descarga propia. |
| Alcance del evaluador | El rol evaluador requiere pertenecer a un comité de la convocatoria para acceder a expedientes ajenos. `test_evaluador_no_asignado_no_revisa` y la nueva regresión HTTP cubren evaluación, detalle, documento, listado y solicitud de correcciones sin comité de esa convocatoria, incluso perteneciendo a otro comité. Administradores y aprobadores conservan su alcance ya existente. No se añade un requisito de comité para estos otros roles. |
| Doble aprobación | Si el monto es estrictamente mayor de 10000, la primera aprobación deja `segunda_aprobacion`. La misma cuenta no puede aprobar de nuevo, ni por fachada ni por la restricción única `una_aprobacion_por_persona`. Pruebas existentes verifican 9999.99, 10000 y 12000, otra cuenta y evaluación vigente. El bloqueo de fila en PostgreSQL serializa decisiones sobre el expediente. |
| Correcciones y reenvío | Solo el propietario edita o adjunta en `borrador` y `correcciones`. Solo esos estados permiten enviar. La prueba existente de correcciones ahora comprueba también edición y nueva carga antes del reenvío. La nueva matriz HTTP prueba el rechazo de editar, adjuntar y reenviar en enviada, revisión, segunda aprobación, aprobada, rechazada, activa y completada, sin efectos persistentes. Las evaluaciones previas pierden vigencia al pedir correcciones; se exige reevaluar. |
| Cuenta desactivada | Django ya impedía autenticación y uso de sesiones abiertas en la siguiente petición con su backend normal. La nueva prueba HTTP confirma ese comportamiento para aspirante, evaluador y aprobador. Se corrigió la autorización de la capa de negocio descrita a continuación. |

## Fallo confirmado y corrección

Las llamadas directas a la fachada podían operar con cuentas inactivas; la
comprobación de sesión HTTP no protege por sí sola esa entrada. Una prueba previa
a la corrección falló en siete subcasos: crear, editar, adjuntar, enviar, iniciar
revisión, evaluar y rechazar. El actor se desactivó en base de datos manteniendo
un objeto User previamente cargado con `is_active=True`.

`usuarios.permisos.cuenta_activa` comprueba autenticación, el indicador del objeto
y su vigencia actual en base de datos, sin fiarse solo del objeto en memoria.
`rol_de` no concede roles a esas cuentas. Se aplicó el mismo control a los permisos
de lectura y a la edición/carga que antes solo comprobaban propiedad. No se crea
un backend de autenticación ni se modifican cuentas, sesiones, roles o contraseñas.

La regresión exige PermissionDenied en las siete operaciones, lecturas sin
acceso y ausencia de cambios en documentos, estados, evaluaciones, decisiones,
auditoría y avisos. La prueba anterior de avisos a personal inactivo se ajustó para
producir el envío con el aspirante activo, sin usar como preparación una operación
de revisión de un evaluador desactivado.

Este control no cancela retroactivamente una operación que ya estuviera en curso
cuando se desactiva una cuenta. Tampoco afirma invalidación permanente de sesiones
anteriores después de una eventual reactivación; no se inventó esa política.

## Documentos: texto frente a validación ejecutable

`Convocatoria.requisitos` es un TextField que se muestra en la convocatoria, no
un catálogo estructurado con casillas de verificación. Los ejemplos de seed_demo
mencionan constancia de estudios, certificación de notas y carta de motivación.
El código no exige subir uno de cada tipo, ni determina que un archivo genérico
cumpla esos tres requisitos. El texto de motivación del formulario no se equipara
a una carta documental validada.

La carga HTTP pasa por `DocumentoForm`:

- Nombre obligatorio de hasta 160 caracteres y archivo no vacío.
- Máximo 10 MiB por archivo (la interfaz lo denomina 10 MB).
- Extensiones PDF, JPG/JPEG o PNG. La extensión se contrasta con la firma básica
  `%PDF-` para PDF o con el formato de imagen y `Pillow.Image.verify`.
- PDF se comprueba por encabezado; no se analiza exhaustivamente ni se verifica
  identidad, autenticidad, legibilidad académica, malware o cumplimiento del requisito.
- Al enviar se consulta existencia de registros, no se repite la validación del
  contenido ni se verifica disponibilidad del objeto en almacenamiento. Las
  escrituras internas/importaciones confiables no pasan automáticamente por el
  formulario. Referencias rotas o archivos desaparecidos requieren revisión de
  integridad; no se presentan como documentos materialmente verificados.
- Los documentos se guardan fuera de static; su descarga requiere autenticación
  y permiso sobre la solicitud. Las correcciones añaden una nueva versión con
  nombre descriptivo; no eliminan automáticamente las anteriores.

Fotografía de perfil, teléfono y cédula no se convirtieron en requisitos nuevos
para enviar. No se añadieron categorías, detección documental, límites de cupos,
presupuesto ni políticas de identidad.

## Decisiones pendientes del equipo

1. Definir qué documentos son obligatorios por convocatoria y cómo registrar su
   revisión, versiones, vigencia y cumplimiento. La validación de "al menos uno"
   no permite declarar que ya se comprueban todos los requisitos escritos.
2. Resolver qué sucede cuando la corrección debe reenviarse después del cierre.
   Hoy editar y reenviar requieren convocatoria abierta; adjuntar en correcciones
   no reabre el plazo ni sustituye ese control. No se cambió esta política sin acuerdo.
3. Confirmar moneda y periodicidad del umbral de 10000. Se mantiene el comparador
   estricto y la decisión ya acordada de dos cuentas diferentes. Esa distinción es
   por identificador de cuenta; no certifica que correspondan a dos personas reales.
4. Identidad, cupos, presupuesto y reglas adicionales no se deducen del texto de
   ejemplo. Si se requieren para la entrega, deben acordarse expresamente.

El único defecto de código reproducido dentro de estos controles fue la vigencia
de cuenta en la entrada de negocio. No se encontraron nuevos fallos de aislamiento,
comité, doble aprobación ni estados en las rutas examinadas.

## Validación local

- SQLite: **114 pruebas satisfactorias** (110 existentes y cuatro nuevas).
- PostgreSQL 16: **114 pruebas satisfactorias**, en un clúster temporal propio,
  solo por socket local y sin conectar a bases externas.
- Ambos: `check`, `makemigrations --check --dry-run`, migración completa desde cero
  y `migrate --check`, satisfactorios. Esta corrección no requiere migraciones.
- Ambos: `scripts/verificar_reconciliacion.py` satisfactorio en instalación nueva,
  actualización desde develop y transferencia del rediseño; conserva identidades,
  contraseñas, relaciones, archivos y tratamiento de coincidencias ambiguas.
- Las bases de pruebas y de reconciliación se destruyen al finalizar. El clúster
  temporal se detiene al terminar. No se usaron bases, medios ni buzones existentes.
- Sin pruebas nuevas de carga o concurrencia real; no se afirma que se hayan
  realizado. Se reutiliza la protección transaccional y la restricción existentes.
- No se cambian plantillas, CSS ni JavaScript; no se afirma una validación visual
  o manual nueva. Los demás worktrees, su documento de cierre y AWS se conservan.

Los cuatro tests nuevos están en `solicitudes/tests.py` y se ejecutan con la suite
habitual `python manage.py test --noinput`. Para PostgreSQL se debe proporcionar
un entorno aislado con permiso de crear/eliminar exclusivamente bases temporales;
no apuntar ese comando a producción. Publicar esta rama y su PR no despliega AWS
ni fusiona ramas.
