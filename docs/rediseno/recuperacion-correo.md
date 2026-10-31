# Recuperación de contraseña por correo

Incremento local del 30 de octubre de 2026 (America/Guatemala), en
`~/Documents/GuateBecas-recuperacion`, rama `feature/recuperacion-correo`, basada
en `origin/feature/foto-perfil` 880bfb4. Incremento inicial publicado en d3dd3f2; esta actualización agrega TLS publicable,
validación real y un plan AWS pendiente. No se han fusionado ramas ni modificado AWS. `chore/cierre-entrega` y su documento pendiente se conservan.
No se alteró el diseño: se reutilizan base.html, estilos y formularios existentes;
solo se añade «¿Olvidaste tu contraseña?» al acceso y las pantallas del flujo.

## Flujo y alcance

Se usan PasswordResetForm, PasswordResetView, PasswordResetConfirmView,
PasswordResetDoneView, PasswordResetCompleteView y el generador de tokens estándar
de Django. El usuario solicita un enlace, establece y confirma la contraseña y
vuelve a iniciar sesión; no hay inicio de sesión automático al restablecerla.
Las validaciones de contraseña son las existentes de Django. El enlace temporal
vence por defecto en una hora y queda invalidado después del cambio de contraseña;
también se comprueban tokens alterados, uid inválido y enlaces reutilizados.
La solicitud por sí sola no cambia ninguna contraseña, identidad ni rol.

Rutas:

- `/recuperar/`: solicitud por correo con POST y CSRF.
- `/recuperar/solicitado/`: respuesta genérica común.
- `/recuperar/<uidb64>/<token>/`: confirmación estándar Django; el token se retira
  de la URL mediante su redirección a set-password y sesión temporal.
- `/recuperar/completado/`: confirmación y enlace para entrar.

Referencia técnica: [autenticación de Django 5.2](https://docs.djangoproject.com/en/5.2/topics/auth/default/)
y [backends de correo](https://docs.djangoproject.com/en/5.2/topics/email/).
No se implementan verificación obligatoria del correo, push, correos de expediente
ni inscripción de un proveedor real. Recuperar una clave no certifica que la
identidad histórica o los datos del expediente sean correctos.

## Respuesta uniforme y correos duplicados

Para un correo sintácticamente válido, registrado o no, ambiguo, inactivo,
inutilizable o limitado se devuelve la misma redirección y página genérica.
Un error de sintaxis del correo muestra la validación habitual del formulario,
sin consultar ni revelar la existencia de una cuenta.

Se exige una sola coincidencia case-insensitive, contando también cuentas
inactivas y contraseñas inutilizables al detectar ambigüedad. Solo se envía para
una cuenta única, activa y con contraseña utilizable. No se selecciona una cuenta
por antigüedad, username, rol o primera coincidencia. No se reescriben direcciones
ni se fusionan cuentas. El trabajador revalida las condiciones antes de enviar y
la confirmación vuelve a comprobar cuenta activa y correo único.

**Limitación histórica:** los correos duplicados quedan sin recuperación automática.
El equipo deberá revisarlos mediante un procedimiento de identidad autorizado,
sin revelar otras cuentas, inventar identificadores o conceder privilegios.
El acceso normal por username no cambia. No se crean restricciones únicas nuevas
sobre User.email que rompan los datos históricos. La comparación sigue las reglas
Django/iexact del motor; no se interpreta que alias con puntos o sufijos sean la
misma dirección. No hay verificación de titularidad de correo previa.

## Cola y comportamiento ante fallos

La migración 0006 añade dos tablas independientes: LimiteRecuperacion y
SolicitudRecuperacion. No modifica usuarios, hashes de contraseña ni Perfil.
La vista registra una solicitud incluso para correos desconocidos o ambiguos
(sin usuario asociado), salvo que se alcance un límite. El envío se procesa fuera
de HTTP para que la latencia/fallo SMTP no sea una diferencia observable directa
en la respuesta de existencia de cuenta. No es una garantía criptográfica de
latencia constante: consultas y rate limiting siguen teniendo tiempos variables.

La cola conserva referencia opcional al usuario, origen del enlace y huellas HMAC
de correo/contraseña, no el correo en claro, IP, token ni clave en claro. Si cambia
el correo o hash antes de procesar, o la solicitud en cola supera el timeout, se
omite. Los tokens solo se generan al procesar solicitudes todavía válidas.

Estados: pendiente → procesando → aceptado, omitido o fallido. «Aceptado» significa
que el backend aceptó el mensaje: **no confirma entrega a una bandeja**. Consola,
locmem o archivo tampoco representan entrega externa. Los fallos no cambian la
cuenta, respuesta web o contraseña; se registra un código genérico sin detalles
SMTP, destinatario o token. Un fallo de persistencia tampoco revela la cuenta.

Se necesita un trabajador independiente usando los mismos settings/base que la web:

```bash
python manage.py procesar_recuperaciones --limit 50
# O proceso de larga duración, supervisado por el operador:
python manage.py procesar_recuperaciones --watch --interval 2
# Mantenimiento explícito de metadatos antiguos, no de usuarios:
python manage.py procesar_recuperaciones --limpiar --limit 50
```

--limpiar elimina límites de más de un día y solicitudes ya retiradas de pendiente
con más de siete días. Los mensajes de prueba en archivos se limpian por separado.
Con PostgreSQL, el reclamo usa select_for_update(skip_locked=True); para SQLite se
prevé un solo trabajador local. No hay reintentos SMTP automáticos: podrían duplicar
mensajes si el proveedor aceptó el envío antes de un corte. El usuario puede pedir
un enlace nuevo respetando límites. Si el trabajador muere con un registro en
procesando, un operador deberá revisar el caso; no se reencola ciegamente.
Supervisión, alertas, pruebas de reinicio y concurrencia con carga real quedan
pendientes antes de habilitar el incremento en el servidor compartido.

## Límites y Nginx como proxy

Por defecto se admiten 3 solicitudes por correo y 20 por IP en ventanas de 900
segundos. Los contadores están en base de datos con actualización transaccional,
compartidos entre workers Gunicorn; no dependen de una caché local por proceso.
Se cuentan también correos desconocidos. La respuesta de límite sigue siendo
la página genérica. Son límites ajustables, no protección completa contra DDoS;
un ataque distribuido puede consumir temporalmente el cupo de una dirección.

Se usa REMOTE_ADDR por defecto. X-Forwarded-For solo se considera cuando el peer
está en PASSWORD_RESET_TRUSTED_PROXIES y contiene exactamente una IP válida.
No se toma arbitrariamente la primera IP de una cadena enviada por el cliente.
Si el encabezado es inválido, se conserva la IP del peer. Sin configuración del
proxy, los usuarios detrás de Nginx compartirían la cuota del proxy.

Para Nginx único frente a Gunicorn, la configuración futura debe **reemplazar**,
no concatenar, el encabezado:

```nginx
proxy_set_header X-Forwarded-For $remote_addr;
```

Configurar exclusivamente el peer real de Nginx (por ejemplo loopback si así está
desplegado) en PASSWORD_RESET_TRUSTED_PROXIES; no confiar en todas las redes ni
usar 0.0.0.0/0. Bloquear acceso público directo a Gunicorn y verificar esta frontera.
Si hay ALB/CDN u otro salto, revisar primero la cadena y cómo Nginx obtiene la IP
real. No basta copiar el ejemplo. No se cambió Nginx ni AWS en esta entrega.

## Configuración SMTP por entorno

.env.example es una plantilla y no se carga automáticamente. Exportar variables
o inyectarlas desde un gestor/archivo privado con permisos adecuados; credenciales
fuera de Git y de la conversación. Web y trabajador deben compartir configuración.

| Variable | Uso |
|---|---|
| EMAIL_BACKEND | Consola local por defecto; SMTP real usa usuarios.email_backend.EmailBackend |
| EMAIL_HOST / EMAIL_PORT | Host y puerto del proveedor; usualmente 587 STARTTLS o 465 TLS implícito, confirmar con él |
| EMAIL_USE_TLS / EMAIL_USE_SSL | Activar exactamente el modo adecuado; no ambos. Para 465: SSL=true, TLS=false |
| EMAIL_HOST_USER / EMAIL_HOST_PASSWORD | Autenticación privada. No incluir valores en Git, documentos o chat |
| EMAIL_TIMEOUT | Tiempo de conexión/envío; 10 segundos predeterminados |
| DEFAULT_FROM_EMAIL | Remitente autorizado por el proveedor, con nombre visible si corresponde |
| EMAIL_CA_BUNDLE | Almacén CA opcional para el backend publicado; mantiene certificado/hostname verificados; no es una clave privada |
| EMAIL_FILE_PATH | Solo backend de archivo local; directorio privado fuera de static/media pública |
| PASSWORD_RESET_PUBLIC_ORIGIN | Origen público HTTPS canónico, sin ruta, query ni credenciales. Evita construir enlaces a partir de Host/X-Forwarded-Host del cliente |
| PASSWORD_RESET_TIMEOUT | Vida del token y máximo de espera en cola, 3600 segundos |
| PASSWORD_RESET_TRUSTED_PROXIES | Peers/redes explícitos de confianza, vacío por defecto |
| PASSWORD_RESET_RATE_WINDOW | Ventana de límites, 900 segundos |
| PASSWORD_RESET_EMAIL_LIMIT / PASSWORD_RESET_IP_LIMIT | Cupos, 3 y 20 respectivamente |

Los checks comprueban TLS/SSL mutuamente excluyentes, límites positivos, redes
válidas, host SMTP y formato del origen. `check --deploy` exige origen público
cuando DEBUG=false y transporte seguro para SMTP público. La vista tampoco genera
enlaces de producción sin origen configurado. En DEBUG local se puede derivar del
host admitido si no se definió origen; la vista previa lo fija explícitamente.

Antes de operar en producción, ejecutar check --deploy con la configuración real
(y resolver también las recomendaciones generales Django), aplicar 0006 mediante
un plan aprobado y habilitar/supervisar el trabajador. No se realizaron estas
acciones en AWS. No se incluyeron nuevas credenciales ni secretos de ejemplo reales.

### Datos no secretos que faltan para conectar un proveedor real

1. Proveedor y región, si aplica; hostname SMTP, puerto y modo STARTTLS/SSL.
2. Método de autenticación SMTP admitido. Si requiere un mecanismo distinto al
   SMTP usuario/clave soportado aquí, revisar la integración antes de prometerla.
3. Dirección de remitente funcional autorizada, nombre visible y dominio de envío.
4. Dominio HTTPS público definitivo de GuateBecas para el enlace (DuckDNS si es el
   elegido), sin claves ni URLs con credenciales.
5. Estado de verificación del remitente/dominio y registros SPF/DKIM/DMARC que el
   proveedor indique; restricciones de sandbox, destinatarios permitidos y cuotas.
6. Peer/topología real Nginx–Gunicorn y decisión sobre límites para usuarios que
   comparten NAT; ubicación del trabajador y mecanismo de supervisión.

Las credenciales se configurarán privadamente por el responsable; **no hace falta
compartir contraseñas aquí**. Aún falta comprobar entrega real, carpeta spam,
rebotes, caducidad y uso del enlace en el dominio público, y respuesta ante caída
real del proveedor. No se afirma que SPF/DKIM/DMARC estén configurados.

## Pruebas y resultados de este incremento

- **102 pruebas aprobadas en SQLite y 102 en PostgreSQL 16.9**, con Python 3.13.3
  y Django 5.2.18. Son 73 existentes y 29 nuevas. Datos sintéticos y destinos nuevos;
  no se usaron bases de desarrollo ni AWS.
- Flujo completo, clave débil/desigual, token inválido/uid falso, expiración,
  reutilización, vínculo de otra cuenta, cuenta inactivada, duplicado creado antes
  o después de emitir el enlace, e identidad/contacto conservados.
- Igualdad de respuesta, ningún envío SMTP durante HTTP, direcciones desconocidas,
  inactivas o no utilizables, límites por IP/correo, renovación de ventana, HMAC,
  proxy confiable/no confiable, encabezado falsificado y origen canónico.
- Fallos de persistencia, OSError, SMTPException y cero mensajes aceptados;
  credenciales/detalles no se registran. SMTP STARTTLS y autenticación comprobados
  con transporte simulado: **sin conexión al proveedor ni entrega real**.
- Check, makemigrations --check --dry-run, migraciones y migrate --check aprobados
  sobre bases nuevas en ambos motores. Los tres escenarios del script de
  reconciliación (cero, develop y rediseño previo) siguen pasando en ambos.
- Chrome local: 25 combinaciones (acceso, solicitud, respuesta, enlace inválido y
  formulario de nueva clave) en 360, 390, 768, 1024 y 1440 px, sin desbordamientos ni
  errores JavaScript. Flujo móvil de cuenta ficticia en 390 px, contraseña débil
  rechazada, guardado y login correctos, reutilización bloqueada. Captura de 360 px
  inspeccionada; no se modificaron CSS, navegación, encabezado ni perfil existente.
- No se ejecutó prueba de carga ni carrera simultánea real entre procesos.
  Confirmar multiworker/proxy y políticas de retención en entorno de ensayo antes
  de producción. No se atribuye aceptación manual al usuario ni al equipo.

## Vista previa local, sin envío externo

Aplicación: **http://192.168.1.21:8005/acceso/**.
Solicitud directa: **http://192.168.1.21:8005/recuperar/**.
Buzón de prueba: **http://192.168.1.21:8005/demo-correo/**.
En la Mac también se puede abrir localhost:8005, pero los enlaces de demostración
usan la IP Wi-Fi configurada; otro cambio de red requiere revisar ese origen.

Se copió en modo lectura la base de 8004 a `.local/recuperacion-demo.sqlite3` y
sus archivos a `.local/media`. Se verificó conservación de usuarios, hashes,
privilegios, perfiles y expedientes originales antes de añadir una cuenta ficticia
nueva `recuperacion.demo`, con correo **recuperacion@demo.invalid**. No se cambió
ninguna cuenta copiada. La prueba de navegador restableció solo esa cuenta ficticia.
Las fuentes permanecen independientes e intactas; sus servidores no se reiniciaron.

Para validar sin usar un correo personal:

1. Solicitar recuperación para **recuperacion@demo.invalid**.
2. Esperar unos segundos y abrir/recargar `/demo-correo/`; seguir «Abrir enlace de
   prueba». El trabajador local ya está activo y usa backend de archivos privados.
3. Establecer una clave nueva y entrar como **recuperacion.demo** con esa clave.
4. Intentar reutilizar el enlace o usar uno alterado; debe aparecer «Enlace no válido».
5. Tras tres solicitudes por dirección en 15 minutos se conserva la respuesta
   genérica pero no se genera otro mensaje; esperar la ventana antes de repetir.

/demo-correo/ existe solo en el URLconf privado de esta vista, no en las rutas
versionadas ni en producción. Muestra únicamente mensajes de la cuenta ficticia,
nunca de las cuentas copiadas. Es una herramienta de prueba en la LAN: cualquiera
con acceso al enlace puede recuperar esa cuenta sin privilegios, deliberadamente
ficticia; no usarla con datos reales. Los archivos de correo contienen enlaces
sensibles, por lo que .local, logs, configuración, SQLite, media, venv y capturas
permanecen excluidos de Git. No se publican enlaces/token en la documentación.
Secreto y cookies de sesión/CSRF son independientes de las otras vistas.

La demostración inicial de **8005** no acredita envío a una bandeja real. El primer mensaje
visible podría pertenecer a la prueba automatizada y estar ya utilizado: pedir
uno nuevo antes de validar. En ese hito quedaban pendientes proveedor y entrega
real; la prueba posterior con Gmail se registra más abajo. No se implementaron push ni correos por cambios de expediente.


## Validación manual confirmada por el usuario

El usuario confirmó el flujo en la vista previa local de recuperación:

- Solicitud de recuperación de contraseña.
- Disponibilidad del enlace en el buzón local de pruebas.
- Cambio de contraseña completado.
- Acceso correcto con la contraseña nueva.
- Rechazo al intentar reutilizar el mismo enlace.

No se incluyen direcciones personales, contraseñas, tokens ni otros datos que
identifiquen la cuenta. Esta confirmación acredita el flujo local con backend de
pruebas, no entrega real por SMTP ni funcionamiento del proveedor en AWS.


## Validación manual posterior con correo real (8006)

El usuario confirmó el flujo completo en una vista previa independiente de 8006:

- Solicitud de recuperación desde el formulario de esa vista.
- Recepción del mensaje real en Gmail.
- Apertura del enlace recibido, dirigido a la vista local.
- Cambio de contraseña completado.
- Inicio de sesión satisfactorio con la contraseña nueva.

No se incluyen correo personal, contraseña, token, identificadores privados ni
capturas. La cuenta de prueba pertenecía a una base separada, sin modificar las
cuentas originales ni el servidor/buzón de 8005. Se conserva como evidencia del
flujo local con Gmail real, distinta de la prueba anterior de buzón de archivos.
No acredita despliegue de recuperación en AWS ni aceptación del equipo/docente.

## TLS reproducible en código publicado

La prueba de 8006 usó inicialmente un backend privado para corregir la confianza
CA de Python en esta Mac. Ese arreglo no bastaba como entrega publicable.
Ahora `usuarios/email_backend.py` contiene un backend SMTP configurable con
`EMAIL_CA_BUNDLE`, que crea un contexto TLS verificado y también puede usar las
CA predeterminadas del runtime. No importa código de .local ni contiene rutas de
secretos o credenciales. Configurar EMAIL_BACKEND=usuarios.email_backend.EmailBackend
para SMTP. En esta Mac se comprobó /etc/ssl/cert.pem; en Ubuntu se prepara el
almacén del sistema, no se traslada un archivo privado de la Mac.
Una CA inválida falla cerrada: no se suprime la verificación de certificado o
hostname. El certificado cliente de Django sigue siendo independiente del CA.

Se probó nuevamente el backend **publicado** desde un proceso Django, con la CA
configurada, STARTTLS y autenticación reales, CERT_REQUIRED y check_hostname
activos, bloqueando todos los métodos de envío. No se envió un nuevo mensaje en
esa comprobación. Este chequeo verifica transporte/autenticación del código
publicado; la recepción del flujo completo fue la confirmación manual previa
sobre 8006, no un reenvío atribuido al nuevo backend.

Resultado actual: **110 pruebas aprobadas por motor** (102 anteriores + 8 nuevas)
en SQLite y PostgreSQL 16.9. Las nuevas comprueban contexto estricto, CA explícita,
CA ausente/inválida, transporte STARTTLS, trabajador con backend publicado y URL
HTTPS, rutas privadas 404 con DEBUG=false y rechazo de backends/URLconf privados
en checks de despliegue. Migraciones sin pendientes y reconciliación desde cero,
develop y rediseño previo aprobadas en ambos motores sobre bases desechables.
No hay nueva migración en esta actualización TLS: continúa 0006 del incremento.

## Producción y entrega siguiente

El URLconf publicado nunca incluye /demo-correo/ ni los buzones privados; las
pruebas con DEBUG=false comprueban 404 para /demo-correo/, /correos/ y /.local/correos/.
check --deploy rechaza backend de pruebas/privado y un URLconf no publicado.
Esto verifica código y configuración prevista, **no inspecciona el servidor AWS**.
Las vistas locales de prueba se conservan deliberadamente: no son producción.
El fragmento Nginx de entrega también bloquea esas rutas y evita access logs de
recuperación con tokens. Deben revisarse otros logs antes de activar en AWS.

Plan, respaldo previo, restauración de ensayo, trabajador systemd, configuración
compartida y reversión no destructiva:
[docs/despliegue/recuperacion-aws.md](../despliegue/recuperacion-aws.md).
Plantillas revisables en deploy/recuperacion/, sin credenciales reales. Requieren
adaptar usuario, rutas, dominio y upstream y validarse con herramientas Linux.
No se instalaron servicios, habilitaron alertas, ejecutaron respaldos ni migraciones
en AWS. Pendientes: revisión humana, ensayo/ejecución autorizados, verificación de
backup/restauración y validación final del flujo en el dominio HTTPS público.
