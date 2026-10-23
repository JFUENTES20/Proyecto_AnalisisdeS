# Menú móvil · mejora local

23 de octubre de 2026. Rama `feature/menu-movil`, creada desde
`origin/integration/guatebecas-develop` en 8e290df. Mejora guardada en un commit
local, pendiente de publicación; la rama de integración y el PR #6 conservan su contenido.

## Comportamiento

- Hasta 800 px: botón Menú de al menos 44 px, icono hamburguesa/cierre,
  nombre accesible dinámico, aria-expanded y aria-controls.
- Más de 800 px: navegación visible sin botón. Sin JavaScript también se
  mantienen los enlaces disponibles, sin presentar un control inoperante.
- Conserva los enlaces de invitado y de sesión, contador de avisos y salida
  mediante formulario POST con CSRF. No intercepta ni convierte la salida a GET.
- Apertura/cierre mediante toque o Enter/Espacio; Tab normal sin atrapar foco;
  Escape cierra y devuelve el foco al botón. También cierra al salir del menú,
  pulsar fuera o seguir un enlace. Las anclas de la misma página reciben el foco.
- El cambio de breakpoint sincroniza visibilidad y foco. Se conserva la identidad
  azul/blanco/jade, sin overlays ni recortes para ocultar desbordamientos.

## Verificación local

Chrome headless instalado en esta Mac, con Playwright y emulación de eventos táctiles.

| Ancho | Sin sesión | Con sesión |
|---|---|---|
| 360 | Menú, toque y teclado OK | Menú, contador y teclado OK |
| 390 | Menú, toque y teclado OK | Menú, contador y teclado OK |
| 768 | Menú, toque y teclado OK | Menú, contador y teclado OK |
| 1024 | Navegación visible y teclado OK | Navegación visible y teclado OK |
| 1440 | Navegación visible y teclado OK | Navegación visible y teclado OK |

Las diez combinaciones no presentan desbordamiento horizontal ni errores JavaScript.
Se verificaron cierre con Escape desde un enlace, retorno de foco, Enter/Espacio,
Tab/Shift+Tab, enlaces ocultos fuera del recorrido de Tab, clic exterior, ancla de
convocatorias, redimensionado y disponibilidad sin JavaScript en ambos estados.
El foco de teclado se comprobó con contorno visible de 3 px. Se inspeccionaron
capturas de cabeceras de teléfono y computadora.

Se navegaron Mi panel, Expedientes y Avisos desde el menú. Salir envió POST con
csrfmiddlewaretoken y terminó la sesión; el mismo POST sin token recibió HTTP 403.
El contador mostró un aviso ficticio pendiente. La suite existente pasó 39/39
con configuración de cookies estándar en una base de tests independiente. Las
pruebas de navegador verificaron además los nombres de cookies propios del preview.

Capturas y reporte local: `.local/menu-evidencias/resultados.json` y PNG en la
misma carpeta, excluidos de Git. La emulación táctil se complementa con la
confirmación manual del usuario indicada abajo. El navegador y sistema del teléfono
no se especificaron; no se acredita cobertura general de Safari/iOS ni lector de pantalla.

## Vista previa independiente

Puerto 8002; base nueva `.local/menu-demo.sqlite3` y archivos ficticios en
`.local/menu-media/`. Sesión `guatebecas_menu_session` y CSRF `guatebecas_menu_csrf`,
para no reemplazar cookies del servidor original aunque se compartan host y navegador.
La contraseña de estas cuentas ficticias es propia de este preview y está en
`.local/menu-demo.json` (permisos 600, excluido de Git). Usuario: `aspirante.demo`.

Servidor original conservado en su puerto y worktree. No se aplicaron migraciones
sobre sus bases, no se copiaron sus credenciales y no se reinició ese proceso.

## Prueba manual confirmada por el usuario · 23 de octubre de 2026

El usuario confirmó en su teléfono, sobre la vista previa del puerto 8002:

- Apertura y cierre del menú sin sesión.
- Navegación con sesión de aspirante.
- Acceso al panel y a los avisos.

Esta evidencia manual es distinta de las pruebas automatizadas y no implica que
se hayan probado otros dispositivos, navegadores o lectores de pantalla.

Se comprobó por separado, mediante consultas SQLite de solo lectura, que los
servidores usan bases diferentes:

| Servidor | Base | Expediente 1 al comprobarlo |
|---|---|---|
| Original, 8000 | `../GuateBecas/db.sqlite3` | Aprobada; monto 12000; aprobador.uno y aprobador.dos registrados |
| Vista previa, 8002 | `.local/menu-demo.sqlite3` | Enviada (`pendiente`); monto 8000; datos ficticios independientes |

El número 1 en ambas bases no identifica el mismo registro compartido. El contador
«En proceso» también incluye solicitudes enviadas. El expediente aprobado original
permanece intacto: no se modificaron estados, sincronizaron bases ni reiniciaron
servidores para esta comprobación o para guardar la mejora en Git.
