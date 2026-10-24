# Fotografía opcional y encabezado del perfil

## Rama y alcance

Worktree independiente: `~/Documents/GuateBecas-foto`, rama `feature/foto-perfil`,
creada desde `origin/feature/perfil-contacto` en fd0d092. Antes de publicar la
mejora se actualizaron las referencias correctamente: la rama remota de contacto
sigue en fd0d092, sin avances respecto al ancestro utilizado. No fue necesario
cambiar la base. La entrega se guarda en su propia rama, sin integrar ramas ni
abrir nuevos PR. Los worktrees anteriores no recibieron cambios.

El encabezado muestra nombre completo (o usuario si no hay nombre), nombre de
usuario y una fotografía circular de 112 px. Sin foto aparecen las iniciales.
No se editan nombres, correo, identificación, roles ni contraseñas. La fotografía
es opcional: ningún requisito de solicitud o regla de becas depende de ella.
La pantalla mantiene el teléfono y su validación nacional 2–8, incluida la
confirmación explícita de discrepancias históricas.

## Procesamiento y privacidad

Se admite JPG/JPEG o PNG de hasta 2 × 1024 × 1024 bytes. Se comprueban el tamaño
real leído, extensión y formato detectado por Pillow, sin confiar en el MIME del
cliente. Pillow verifica la integridad y decodifica el contenido. Se rechazan
archivos corruptos, formatos distintos, animación y dimensiones superiores a
6000 px por lado o 12 millones de píxeles; se mantienen las protecciones de Pillow
contra imágenes de descompresión excesiva.

Se aplica orientación EXIF, recorte cuadrado centrado y remuestreo a 512 × 512.
Un lienzo RGB nuevo elimina los metadatos; la transparencia se compone sobre
blanco. Solo se guarda un JPEG optimizado a calidad 85, con nombre UUID generado
por el servidor. No se guarda el original ni su nombre o EXIF. Las referencias de
implementación son la documentación oficial de [Image.verify](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.verify)
y [ImageOps.exif_transpose / fit](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html).
Pillow 12.3.0 ya formaba parte de requirements.txt; no se cambian dependencias.

Las imágenes están en MEDIA_ROOT/perfiles, fuera de static. No se añadió ninguna
ruta pública de media. La entrega se realiza mediante GET/HEAD autenticado en
`/mi-perfil/fotografia/<usuario_id>/`, exclusivamente para el aspirante propietario;
otra cuenta obtiene 404 y sin sesión se exige acceso. La respuesta es image/jpeg,
con Cache-Control private, no-store y protección nosniff de Django.

Guardar, reemplazar y eliminar requieren POST y CSRF en
`/mi-perfil/fotografia/`. El destino siempre se obtiene de la sesión, sin aceptar
identificadores ni campos extra del cliente. Otros roles no pueden modificar fotos.
La administración muestra el campo como solo lectura para no eludir este flujo.

El nuevo campo Perfil.fotografia es opcional. La migración 0005 agrega ese campo y
EventoFotografia (responsable, perfil, fecha, operación y resultado), sin migrar
ni sobrescribir datos históricos. Cambio y auditoría son transaccionales. En caso
de fallo de auditoría se revierte la base y se limpia el archivo nuevo; el anterior
se elimina solo después del commit. Si falla esa limpieza del almacenamiento se
registra el error y puede quedar un archivo huérfano para revisión, conservando
la referencia vigente. No se promete atomicidad entre una base y el filesystem.

## Interfaz

El selector muestra una vista previa circular local antes de guardar, claramente
marcada «aún no guardada». El archivo no se envía hasta pulsar el botón de guardar.
Los errores del cliente complementan, sin reemplazar, la validación del servidor.
El nombre de archivo se muestra aparte y puede envolver, evitando cortes del
texto nativo en teléfonos. Cambiar foto y eliminar son formularios independientes
del teléfono. Al eliminar vuelven las iniciales. Se mantiene navegación accesible,
foco, colores azul/blanco/jade y el pie de proyecto universitario de demostración.

## Vista previa aislada

Desde la misma Wi-Fi: **http://192.168.1.20:8004/mi-perfil/**.
En la Mac: **http://localhost:8004/mi-perfil/**.

La base de 8003 se copió mediante backup SQLite en modo lectura a
`.local/foto-demo.sqlite3` y sus archivos a `.local/foto-media`. La migración solo
se aplicó a esta copia. Las cuentas ya registradas conservan sus credenciales:
no se ejecutó seed_demo ni se restablecieron contraseñas. Se verificaron todas las
filas originales usando las columnas previas a 0005: identidades, hashes,
privilegios, teléfono, historial, expedientes, documentos y avisos se conservaron.
Django añadió los nuevos metadatos de modelo/permisos, sin concederlos a cuentas.

Hay secreto y nombres de cookies distintos de las otras vistas. Hosts permitidos:
localhost, 127.0.0.1 y 192.168.1.20, sin comodines. La configuración, bases,
archivos cargados, evidencia y entorno virtual permanecen ignorados por Git.
Las sesiones y cambios posteriores de cada copia son independientes.
Los servidores 8000, 8002 y 8003 no se reiniciaron; sus bases se conservaron.

## Comprobaciones

- Django check sin problemas; makemigrations --check --dry-run sin pendientes;
  migrate --check aprobado en la copia de 8004.
- **73 pruebas aprobadas en SQLite y 73 en PostgreSQL 16.9**: 56 existentes y
  17 nuevas. Las nuevas cubren encabezado/iniciales, JPG y PNG, orientación y
  eliminación de EXIF, transparencia, tamaño/dimensiones, corrupción y animación,
  MIME falso, guardado/reemplazo/eliminación y limpieza, auditoría y rollback,
  CSRF, roles, acceso de otra cuenta y conservación de identidad y teléfono.
- Reconciliación en ambos motores: instalación desde cero, actualización del
  esquema publicado de develop y transferencia del rediseño previo aprobadas.
  Se conservaron cuentas, contraseñas, relaciones, archivos y expedientes;
  los correos ambiguos permanecen pendientes sin asignaciones automáticas.
  Solo se usaron bases nuevas desechables y un PostgreSQL temporal local.
- transferir_redisenio excluye el campo fotografia al leer/verificar el origen
  antiguo, que no tiene esa columna. Su alcance sigue siendo el rediseño previo,
  sin Aspirante; no es una herramienta para fusionar bases actuales con fotos.
  El generador de fixtures de verificación adapta únicamente el modelo en memoria
  del subproceso histórico a ese esquema. No se utiliza --fake ni se cambia la
  migración inicial publicada.
- Chrome local a **360, 390, 768, 1024 y 1440 px**: acceso desde el menú, iniciales,
  vista previa antes de guardar, subida PNG, reemplazo JPG, eliminación, rechazo
  de formato en cliente, acceso sin sesión rechazado y teléfono conservado. Sin
  desbordamientos horizontales ni errores JavaScript; cierre del menú con Escape.
  Capturas de 360 y 1440 inspeccionadas visualmente. Se usaron imágenes geométricas
  propias y la cuenta ficticia de demostración, nunca la cuenta personal copiada.
  Evidencia privada: `.local/foto-evidencias/`.

Pendiente: ampliar cobertura de navegadores y dispositivos físicos distintos
al teléfono utilizado por el usuario. El recorte es centrado automático, sin editor de encuadre.
No se acredita concurrencia productiva con SQLite, que no ofrece bloqueo de fila.
PWA, push y despliegue permanecen fuera de esta entrega.


## Ajustes de presentación antes de guardar

Se usa «MI CUENTA GUATEBECAS» como encabezado superior. El teléfono vigente,
el histórico cuando corresponde y el formulario se reúnen en una sola tarjeta
«Contacto», conservando etiquetas, confirmaciones, validaciones y resultados.
La ayuda principal de fotografía es «JPG o PNG, máximo 2 MB». Los límites de
resolución se mantienen; si se superan, cliente y servidor indican reducir las
dimensiones en un editor hasta cumplir 12 megapíxeles y 6000 píxeles por lado,
y volver a seleccionar el archivo.
Cuando hay foto, el selector vacío muestra «Selecciona una imagen nueva para
cambiar tu fotografía», también tras cancelar o rechazar una selección.
Se conservan avatar, nombre, usuario, vista previa y operaciones protegidas.

Se volvieron a aprobar las 73 pruebas SQLite. La revisión en Chrome a 360, 390,
768, 1024 y 1440 px comprobó la tarjeta única, ayudas, indicación con foto existente,
vista previa, guardado/reemplazo/eliminación, rechazo de teléfono inválido y
conservación del valor vigente. No hubo desbordamientos ni errores JavaScript.
Los envíos se probaron sobre una copia temporal de la base y los archivos de
8004, eliminada al terminar; las cuatro bases de las vistas existentes conservaron
su SHA-256. Solo se reinició 8004 para cargar la presentación actualizada.


## Validación manual confirmada por el usuario

El usuario revisó Mi perfil desde su teléfono en la vista previa independiente
del puerto 8004 y confirmó el funcionamiento de la fotografía, su permanencia
al recargar y su eliminación. El contacto se conservó durante estas operaciones.
También revisó el perfil ajustado y aprobó mantener por ahora la presentación
final: encabezado con avatar, nombre y usuario, tarjeta única de contacto y ayudas
de fotografía simplificadas.

No se incluyen datos personales, números de teléfono, credenciales ni fotografías
del usuario. La confirmación no especifica dispositivo, navegador o ancho exacto,
por lo que no se le atribuye cobertura de otros modelos o navegadores.
