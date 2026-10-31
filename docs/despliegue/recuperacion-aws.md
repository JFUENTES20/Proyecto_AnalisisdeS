# Plan de despliegue y reversión de recuperación — no ejecutado

Estado: instrucciones y plantillas para revisión. El usuario reportó EC2 Ubuntu
24.04, PostgreSQL, Nginx, Gunicorn como servicio, DuckDNS y HTTPS. No se inspeccionó
ni modificó AWS. No se conoce aquí el commit efectivo, rutas, usuario, nombres de
servicios o versión de esquema desplegados. No se afirma automatización,
supervisión instalada, respaldo existente ni restauración comprobada.

Las plantillas en `deploy/recuperacion/` **no se aplican sin adaptar**. Usan rutas y
usuario de ejemplo, un upstream por reemplazar y valores privados por configurar.
El CI comprueba Django y reconciliación; no despliega AWS. No copiar `.local`,
venvs de Mac, SQLite, buzones, secretos o fotos de usuarios al artefacto publicado.

## Condiciones previas y decisiones del operador

1. Registrar release/commit actual y candidata, esquema de usuarios, Python/venv,
   unidad Gunicorn, usuario/grupo, rutas reales, upstream/socket, base/media y
   quién autoriza la ventana. No imprimir Environment ni credenciales en tickets.
2. Si el servidor usa el esquema del rediseño previo con una 0001 de usuarios
   distinta, **detener el plan**: utilizar el procedimiento de transferencia a una
   base nueva de `docs/rediseno/integracion.md`, nunca --fake general. La migración
   0006 de recuperación solo agrega tablas; no convierte ese esquema anterior.
3. Confirmar dominio HTTPS canónico, remitente autorizado, límites del proveedor,
   CA instalada y salida SMTP 587/STARTTLS. Configurar credenciales mediante
   canal privado/gestor; no en argumentos, Git ni chat. Si cambió la clave Google,
   revisar su contraseña de aplicación por el responsable, no registrar su valor.
4. Revisar los PR encadenados y elegir una versión aprobada. No desplegar una rama
   distinta por su nombre sin identificar el SHA. Revisar nuevas migraciones de
   esa versión, no asumir que AWS ya está en 0005 o d3dd3f2.
5. Separar tres evidencias: autenticación SMTP, aceptación del mensaje y recepción
   real. La prueba manual local en 8006 no verifica AWS.

## Respaldo previo y restauración de ensayo

Preparar un directorio privado fuera del webroot, con umask 077. Poner la aplicación
en mantenimiento para **todas las escrituras**, parar nuevos POST y drenar tareas
que estén procesando. Detener el trabajador de recuperación si ya existe; si las
tablas todavía no existen no intentar consultar su cola. No matar un envío activo
sin revisar su resultado: podría haber sido aceptado y quedar en procesando.

Guardar de forma segura:

- Dump completo PostgreSQL en formato custom, compatible con su versión real.
- MEDIA_ROOT completo y metadatos/permisos de documentos y fotos.
- Release anterior/commit, requirements y versiones efectivas del runtime.
- Configuración privada de app/servicios/Nginx y certificados según política,
  cifrada o en repositorio de respaldos protegido; **nunca en este repositorio**.
- Manifest de respaldo con fecha, versión, hashes y alcance; sin valores secretos.

Ejemplo de PostgreSQL a adaptar, con `.pgpass` privado 600 o autenticación local
apropiada. Estas variables no incluyen la contraseña y deben corresponder a la
base y usuario reales, no a una base de demostración:

```bash
umask 077
pg_dump --host="$DB_HOST" --port="${DB_PORT:-5432}" --username="$DB_USER" \
  --dbname="$DB_NAME" --format=custom --file="$BACKUP_DIR/antes-recuperacion.dump"
pg_restore --list "$BACKUP_DIR/antes-recuperacion.dump" > "$BACKUP_DIR/contenido.txt"
```

No basta listar el dump. Restaurar en una **base de ensayo nueva** sin apuntar a
la base activa y usar una copia de media separada; comprobar cuentas, relaciones,
archivos e integridad, sin registrar contraseñas ni datos personales. Comprobar
hashes y permisos de los archivos copiados. Guardar resultados de restauración y
mantener el respaldo protegido/cifrado y fuera de la instancia según política.
No se presenta como respaldado hasta completar esto. Reabrir escrituras solo al
terminar el cambio y verificar consistencia; un dump y media capturados en momentos
distintos con escrituras concurrentes no son una copia coherente garantizada.

## Configuración compartida y confianza TLS reproducible

El backend publicable es `usuarios.email_backend.EmailBackend`. Hereda SMTP de
Django, añade `EMAIL_CA_BUNDLE` opcional para un almacén CA y mantiene
CERT_REQUIRED/check_hostname. Una CA ausente/ilegible o inválida falla cerrada;
no se usa CERT_NONE ni se reintenta sin validación. En Ubuntu puede usarse
`/etc/ssl/certs/ca-certificates.crt`; comprobar instalación/actualización del paquete
ca-certificates. No descargar una CA arbitraria ni usar certificados obtenidos de
una conexión fallida como nueva raíz de confianza. En la Mac se verificó
`/etc/ssl/cert.pem`. Es configurable y no depende de scripts o rutas privadas Mac.
`EMAIL_SSL_CERTFILE`/KEYFILE de Django son para certificado cliente, no sustituyen
el almacén de CA del servidor.

El archivo de ejemplo `recuperacion.env.example` se instala, con valores reales,
fuera del checkout como `/etc/guatebecas/recuperacion.env` (ruta de ejemplo),
root:root 600. Mantener los secretos/base/SECRET_KEY de la app actual en su archivo
privado de entorno, sin sobrescribirlos. Web y trabajador deben usar los mismos
settings, base, SECRET_KEY, origen canónico, backend SMTP y CA. No importar
`gmail_backend`, `recuperacion_settings` o `recuperacion_real_settings` privados.
No cambiar SECRET_KEY para este despliegue: invalidaría sesiones y tokens.

Los EnvironmentFile son formato systemd, no scripts para ejecutar con `source`.
Para comandos de gestión, usar el mecanismo de ejecución de la app existente o
una unidad transitoria con ambos EnvironmentFile, el usuario y cwd correctos;
nunca imprimir las variables completas ni pasar secretos como argumentos.
No se incluye un cargador automático de esos archivos en Django.

## HTTPS y frontera Nginx/Gunicorn

Adaptar el fragmento Nginx en el bloque HTTPS que ya existe. Reemplazar el upstream
con el real y mantener intactos certificados, DNS y rutas de medios privados.
No introducir alias públicos para .local, media privada o archivos de correo.
El URLconf publicado no contiene `/demo-correo/` ni rutas de buzón; el fragmento
las bloquea también en el proxy. Los tests con DEBUG=false comprueban 404.
El check de despliegue rechaza backend de consola/archivo/locmem o módulo privado
y un URLconf distinto al publicado.

Nginx reemplaza X-Forwarded-For con `$remote_addr`. Solo confiar en sus peers reales
en PASSWORD_RESET_TRUSTED_PROXIES y evitar acceso público directo a Gunicorn.
Si existe ALB/CDN, revisar primero cómo Nginx obtiene la IP; no confiar en cabeceras
proporcionadas por el cliente. El límite en base de datos se comparte entre workers.
El fragmento desactiva access log para recuperación por los tokens en la URL;
desactivar o filtrar también los access logs de Gunicorn, observabilidad y proxy
anterior antes de habilitar el flujo, sin publicar los enlaces. El fragmento
Nginx por sí solo no elimina esos otros registros. Los logs de fallo del trabajador usan códigos genéricos sin SMTP crudo.

Verificar la configuración efectiva de HTTPS de la app existente. Este incremento
NO activa confianza global en X-Forwarded-Proto. Si falta la detección del proxy,
configurar de forma controlada `SECURE_PROXY_SSL_HEADER =
('HTTP_X_FORWARDED_PROTO', 'https')` en los settings operativos, solo después de
asegurar que Nginx sobrescribe esa cabecera y que Gunicorn no es público.
Comprobar `request.is_secure`, redirecciones, cookies Secure y CSRF desde HTTPS.
El origen de enlaces se fija siempre en PASSWORD_RESET_PUBLIC_ORIGIN con HTTPS,
no depende de Host o X-Forwarded-Host del cliente. No presentar esa comprobación
como realizada en el servidor: queda pendiente.

## Secuencia de activación — aprobación posterior requerida

1. Con respaldo restaurado en ensayo y mantenimiento activo, preparar un release
   nuevo/venv Linux independiente con requirements.txt. Conservar el release viejo;
   no reutilizar el venv de Mac ni actualizar a ciegas el venv en uso.
2. Validar las plantillas adaptadas: `nginx -t` y `systemd-analyze verify` con los
   archivos y rutas reales. No se han ejecutado esas herramientas en AWS desde aquí.
3. Ejecutar check --deploy --fail-level ERROR y revisar recomendaciones restantes
   en el release candidato con ambos archivos privados de entorno. Verificar
   PostgreSQL y origen HTTPS, backend publicable y CA. El check rechaza buzones de
   prueba/configuración privada en producción; revisar además qué archivos se sirven.
4. Examinar `migrate --plan` con el entorno correcto. Ensayar contra la copia antes
   de ejecutar `migrate --noinput` en la base activa durante la ventana. No ejecutar
   downgrades ni --fake. Comprobar `migrate --check`. 0006 no toca usuarios/claves.
5. Instalar el drop-in del servicio Gunicorn **existente**, sin reemplazar su
   ExecStart o secretos. Si las rutas/servicio difieren de los ejemplos, adaptarlos.
   Instalar la unidad del trabajador separada, inicialmente detenida. Ambos usan
   el mismo release y entorno; todavía no abrir solicitudes a usuarios.
6. Cambiar al release aprobado, recargar systemd y reiniciar Gunicorn de forma
   coordinada con el trabajador parado. Revisar la cola existente antes de
   habilitarlo: pendientes antiguos de un buzón local no deben enviarse por Gmail.
   El plan normal usa una base ya de producción, no una copia de .local con cola.
   No borrar/reencolar registros sin análisis y autorización.
7. Arrancar/habilitar el trabajador supervisado, revisar sus checks iniciales,
   conexión y estado; levantar mantenimiento cuando el sistema esté sano. Abrir
   la recuperación solo entonces. Su primer envío debe proceder de una solicitud
   explícita autorizada, no de un script que cree trabajos ocultamente.
8. Validar desde HTTPS con una cuenta de ensayo autorizada: solicitud genérica,
   recepción real/spam, dominio correcto, cambio de contraseña, acceso, expiración
   y reutilización. Confirmar buzón 404 y aislamiento de cuentas/documentos/fotos.
9. Registrar SHA, operador autorizado, resultados, hora, rollback disponible y
   decisión de aceptación. No dar por hecha la aceptación del equipo o del docente.

## Supervisión y mantenimiento

worker.service.example usa Restart=on-failure, reinicio espaciado y límite de
reintentos para evitar bucles de fallos; tiene umask 0077 y permisos restringidos.
No es un servicio instalado ni monitorización activa. Adaptar usuario/rutas y
permisos: el trabajador solo necesita leer código/CA/entorno y conectar a PostgreSQL.
Con ProtectSystem=strict no debe necesitar escribir al checkout ni a un buzón.

Después de instalar, el operador revisará (nombres de ejemplo):

```bash
systemctl is-active guatebecas-recuperacion.service
systemctl status guatebecas-recuperacion.service --no-pager
journalctl -u guatebecas-recuperacion.service --since '15 minutes ago' --no-pager
```

Agregar alertas reales de unidad inactiva/reinicio repetido, pendientes que superen
el SLA acordado y estados fallido/procesando atascados. No se entrega aquí una
integración de alertas ni se afirma que esté habilitada. Consultar solo agregados
de estado y antigüedad desde un comando de gestión con el entorno apropiado, sin
mostrar correo/token/usuario. Ejemplo ORM de solo lectura:

```python
from django.db.models import Count, Min
from usuarios.models import SolicitudRecuperacion
print(list(SolicitudRecuperacion.objects.values('estado').annotate(
    total=Count('id'), mas_antigua=Min('creada')).order_by('estado')))
```

«Aceptado» solo acredita que SMTP aceptó el mensaje; no confirma recepción ni
lectura. Revisar fallos del proveedor sin loguear credenciales/destinatarios. Si un
proceso muere después de aceptar el mensaje, puede quedar procesando; no hay
reintentos automáticos SMTP porque podrían duplicar envíos. Revisar antes de
reencolar y preferir una nueva solicitud consciente del usuario según límites.
Programar mantenimiento `procesar_recuperaciones --limpiar --limit 50` solo con
el entorno productivo correcto y política aprobada; este comando también procesa
hasta 50 pendientes, no es un borrado puro. No ejecutarlo como ensayo sobre AWS.

## Reversión

- Mantener acceso en mantenimiento para la recuperación. Parar nuevas solicitudes,
  drenar/revisar envíos activos y detener el trabajador antes de cambiar código.
- Si el fallo es de app/configuración y la base sigue consistente: volver al release,
  venv y configuración previos conservando SECRET_KEY, base y media actuales.
  Retirar/deshabilitar la unidad nueva o dejarla detenida; revertir el drop-in y el
  fragmento Nginx si corresponde. Validar nginx -t, recargar/reiniciar controladamente
  y comprobar el servicio anterior. No arrancar el trabajador con código incompatible.
- **No revertir 0006 para borrar sus tablas** como solución general. Son adiciones;
  una app anterior puede ignorarlas. Conservarlas evita perder trazabilidad y es
  preferible al downgrade destructivo. Las solicitudes pendientes quedan pausadas
  y requieren revisión para una futura activación, no envío automático.
- **No restaurar indiscriminadamente el backup sobre la base activa**: después de
  abrir al público podrían existir contraseñas legítimamente cambiadas, nuevas
  cuentas o expedientes. Una restauración total los perdería. Si la base está dañada,
  mantener ventana cerrada y restaurar en una base NUEVA/almacenamiento independiente,
  verificar integridad y aprobar el tratamiento de cambios posteriores antes de
  conmutar. Documentar la pérdida aceptada; nunca simular que el rollback es gratuito.
- Confirmar acceso, estados y archivos tras la reversión sin exponer usuarios.
  Conservar evidencia de la causa, backup y acciones. No cambiar Google, DNS o AWS
  automáticamente desde este repositorio. Recuperación en AWS permanece pendiente
  hasta ejecutar y documentar el plan autorizado.

Referencias: [SMTP Django](https://docs.djangoproject.com/en/5.2/topics/email/),
[contextos TLS de Python](https://docs.python.org/3/library/ssl.html#ssl.create_default_context),
[supervisión systemd](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html).
