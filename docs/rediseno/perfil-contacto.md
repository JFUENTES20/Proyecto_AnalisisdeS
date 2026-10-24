# Perfil y teléfono de contacto

Trabajo local en `feature/perfil-contacto`, creada desde
`origin/feature/textos-convocatorias` (f64a4f3). Esta mejora se guarda en un commit
local, sin publicación ni nuevos PR.

## Validación manual comunicada por el usuario

El 23 de octubre de 2026, el usuario confirmó desde su teléfono, en la vista
previa independiente del puerto 8002: registro de una cuenta nueva, expedientes
y avisos inicialmente vacíos, cierre de sesión e inicio de sesión posterior
correctos. No se registran correo, contraseña ni datos que identifiquen la cuenta.
Esta confirmación corresponde al flujo de registro y acceso existente.

El usuario confirmó también desde su teléfono, en la vista previa independiente
del puerto 8003, la validación de Mi perfil:

- Guardó un número válido y recibió «Teléfono actualizado».
- El formulario rechazó `12345678`.
- Al recargar, el teléfono válido anterior permaneció guardado.

No se incluye el número válido utilizado, ni datos personales o credenciales de
la cuenta. No se especificaron modelo del teléfono, navegador ni ancho de
pantalla; la confirmación no atribuye cobertura adicional a dispositivos concretos.

## Uso y permisos

`/mi-perfil/` permite únicamente al aspirante consultar y actualizar su propio
teléfono. «Mi perfil» aparece en la navegación de escritorio y en el menú móvil.
No recibe identificadores de usuario o perfil: resuelve siempre la sesión actual.
Los campos adicionales en POST se rechazan con 403, incluso intentos de enviar
correo, cédula, roles, contraseñas o identificadores ajenos. Otros roles reciben
403; sin sesión se exige acceso. El formulario mantiene POST con CSRF.

Se aceptan ocho dígitos nacionales que comienzan entre 2 y 8, espacios normales
o inseparables y prefijo opcional `+502`. Se guarda `+502` seguido de ocho dígitos.
Referencia: [Plan Nacional de Numeración de SIT](https://www.sit.gob.gt/plan-nacional-de-numeracion.html).
La [resolución SIT-DSI-226-2022](https://www.sit.gob.gt/files/SIT-DSI-226-2022.pdf)
habilita el bloque 80000000–89999999 para telefonía móvil y fundamenta la admisión
del prefijo nacional 8. La validación es de formato: no comprueba asignación,
titularidad, existencia ni recepción de mensajes.
El teléfono es obligatorio al guardar; no se cambia el registro de cuentas.

## Una fuente vigente y conservación histórica

`Perfil.telefono` es la única fuente para el contacto vigente. `Aspirante.telefono`
permanece como archivo histórico y no se sincroniza después de cada edición.
La migración anterior 0003 sigue conservando su copia inicial para instalaciones
históricas; esta entrega no realiza una nueva copia ni normaliza datos en bloque.
La nueva migración 0004 solo crea `EventoContacto`, sin modificar registros existentes.
Ambos teléfonos se muestran como solo lectura en administración para evitar
ediciones paralelas que omitan el flujo de confirmación y auditoría.

Se comparan valores normalizados, de modo que `5123 4567` y `+50251234567` no
producen una falsa discrepancia. Si difieren (incluido un contacto vigente vacío
con teléfono histórico), se muestran ambos y se exige confirmación explícita
antes de guardar. No se elige un valor automáticamente ni se borra el histórico.
Las discrepancias no confirmadas quedan pendientes del titular; los valores
históricos inválidos se conservan y requieren introducir un contacto válido.
Sin historial no se inventa Aspirante, cédula ni teléfono.

Cada cambio efectivo genera un EventoContacto con responsable, fecha, operación,
resultado y valores anterior/nuevo, en la misma transacción. Repetir el mismo
valor no genera eventos duplicados. Un formulario firmado, ligado al perfil y al
valor visto, expira después de una hora; si el valor cambió, se pide recargar y
revisar antes de escribir. El bloqueo de fila protege la escritura en PostgreSQL.
Un fallo al registrar el evento revierte el cambio. La auditoría conserva datos
personales: no debe publicarse como fixture ni incluirse en capturas compartidas.

## Vista previa y aislamiento

Nueva dirección: `http://192.168.1.20:8003/mi-perfil/` (misma Wi-Fi).
En la Mac: `http://localhost:8003/mi-perfil/`.

Se copió mediante backup SQLite en modo lectura la base de 8002 a
`.local/perfil-demo.sqlite3`, junto a sus archivos cargados en `.local/perfil-media`.
Se verificó igualdad de las filas de cuentas (incluidos hashes de contraseñas),
perfiles, Aspirante y expedientes antes y después de aplicar 0004 a la copia.
Las cuentas creadas en 8002 funcionan con sus mismas credenciales en 8003;
los cambios posteriores pertenecen a cada copia y no se sincronizan.
Se usan secreto y nombres de cookies independientes. No se ejecutó seed_demo
ni se restablecieron contraseñas. Hosts explícitos: localhost, 127.0.0.1 y
192.168.1.20; sin comodines.

Los servidores 8000 y 8002 no se reiniciaron y sus bases no recibieron migraciones
ni actualizaciones de esta mejora. El expediente aprobado original se conserva.
Toda configuración privada, evidencia, copia de base y archivos están bajo `.local`
ignorado por Git; el entorno virtual también está excluido.

## Comprobaciones

- Django check: sin problemas. `makemigrations --check --dry-run`: sin cambios
  de modelos pendientes. `migrate --check` aprobado en la nueva copia de 8003.
- 54 pruebas aprobadas en SQLite y PostgreSQL 16.9: 43 existentes y 11 nuevas.
  PostgreSQL utilizó exclusivamente un clúster temporal local y una base de pruebas
  creada/destruida por Django. SQLite utilizó la base de pruebas en memoria.
- Cobertura nueva: permisos de sesión y roles, CSRF, campos ajenos, tokens de otro
  perfil, números válidos/incorrectos, discrepancias y confirmación, conservación
  de User y Aspirante, bloqueo de formularios obsoletos o alterados, auditoría,
  idempotencia y reversión ante fallo de auditoría.

PWA, push, verificación de correo, recuperación de contraseña y despliegue
permanecen fuera de esta entrega. No se modifican PR existentes ni ramas remotas.

- Chrome local: 360, 390, 768, 1024 y 1440 px, con vista invitada y aspirante.
  Acceso a Mi perfil desde navegación, apertura táctil, teclado y Escape del menú
  angosto, mensajes de validación, guardado normalizado y foco visible en el campo.
  Sin desbordamientos horizontales ni errores JavaScript. Captura de 360 px
  inspeccionada visualmente; mantiene azul, blanco, jade y pie de demostración.
  Evidencia privada ignorada: `.local/perfil-browser.json` y `.local/perfil-*.png`.
- Verificación final: SHA-256 de las bases 8000 y 8002 sin cambios; expediente
  original 1 todavía aprobado. Identidades, hashes de contraseñas y privilegios
  de la copia coinciden con 8002; expedientes idénticos. Las pruebas de navegador
  solo cambiaron el teléfono del aspirante de demostración en 8003 y su last_login.

Limitaciones: los anchos se comprobaron con Chrome automatizado y el usuario
confirmó el flujo descrito desde su teléfono. Queda pendiente ampliar la cobertura
a otros navegadores y dispositivos. No se
realizó una prueba de carga con escrituras simultáneas; se comprobó el rechazo de
formularios obsoletos y el rollback de auditoría. SQLite no ofrece bloqueo de fila
como PostgreSQL, por lo que la vista previa local no acredita concurrencia productiva.


## Corrección del prefijo móvil 8

Se revisó visualmente la página 2 de la resolución oficial SIT-DSI-226-2022:
retira de reserva el indicativo 8 y habilita el bloque 80000000–89999999 para
telefonía móvil. La expresión básica y su mensaje admiten ahora inicios 2–8;
se mantienen espacios, prefijo opcional +502 y normalización internacional.
Esto valida únicamente formato, sin consultar asignación o titularidad.

Resultado: 56 pruebas aprobadas en SQLite y 56 en PostgreSQL 16.9, usando
exclusivamente bases de prueba independientes. Se añadieron casos del bloque 8
con y sin +502, espacios y ambos límites del bloque. Se mantienen longitudes
incorrectas y prefijos rechazados; se comprueba además que, tras un error y una
recarga, permanece el teléfono anterior y no se genera un evento de cambio.
La comprobación de Django no reportó problemas. No requiere nuevas migraciones.

La corrección se guarda en un nuevo commit posterior a b70cd40, sin reescribirlo.
No se aplicaron cambios a bases, archivos cargados ni datos históricos y no se
reiniciaron los servidores de desarrollo existentes. Al usar --noreload, los
procesos activos cargarán la corrección de Python en su próximo reinicio.


### Validación manual posterior a la corrección

El usuario confirmó desde su teléfono, después del reinicio de la vista previa
independiente del puerto 8003, que el formulario aceptó un teléfono con prefijo
nacional 8, rechazó uno con prefijo 9 y conservó el valor válido al recargar.
No se incluye el número utilizado ni otros datos personales de la cuenta.
