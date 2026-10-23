# Adaptación a teléfonos, tablets y computadoras

Verificación local en Chrome headless instalado en macOS, 21 de octubre de 2026.
Rama feature/rediseno-becanet. Se conserva identidad GuateBecas y reglas de negocio.

## Cambios

- Navegación distribuida en rejilla de tres columnas en teléfono, con objetivos
  táctiles de al menos 44 px; enlaces, filtros y botones operables sin precisión fina.
- Campos de 16 px como mínimo para reducir el zoom automático al escribir en iOS;
  ayuda de formularios más legible, foco visible y selector de archivos adaptable.
- Solicitudes presentadas como fichas con etiquetas y enlace completo en teléfono;
  tabla mantenida en tablet/escritorio. No se oculta contenido para disimular overflow.
- Títulos, correos, documentos con nombres largos y avisos ajustan líneas; columnas
  pueden contraerse. Acciones y paginación se acomodan sin superponerse.
- Hero de una columna hasta 800 px; formularios y avisos con botones amplios en móvil.
- Texto de bienvenida actualizado a GuateBecas; movimiento reducido respetado.

## Matriz ejecutada

| Pantalla | 360 | 390 | 768 | 1024 | 1440 |
|---|---|---|---|---|---|
| Registro | OK | OK | OK | OK | OK |
| Acceso | OK | OK | OK | OK | OK |
| Inicio | OK | OK | OK | OK | OK |
| Panel del aspirante | OK | OK | OK | OK | OK |
| Crear solicitud | OK | OK | OK | OK | OK |
| Expediente, edición y carga | OK | OK | OK | OK | OK |
| Listado de solicitudes | OK | OK | OK | OK | OK |
| Notificaciones con avisos | OK | OK | OK | OK | OK |

40 combinaciones: documentElement.scrollWidth <= innerWidth, sin errores JavaScript,
sin controles medidos menores de 44 px (navegación, botones, inputs y selects), y
sin campos de texto menores de 16 px. Altura de medición 900 px. Se inspeccionaron
capturas de teléfono y tablet, además de generarse capturas a 1440 px.
Resultados detallados y muestra de capturas: vistas/responsive/.
La ausencia de overflow no sustituye toda comprobación visual o de accesibilidad.

## Flujo funcional desde teléfono (360 × 800, emulación táctil)

Registro real de cuenta ficticia y acceso; creación de borrador; carga de PDF con
nombre largo; envío; revisión por evaluador; petición de correcciones; apertura de
un aviso desde el aspirante; rechazo de archivo TXT con error visible. Se ejecutó
contra servidor temporal en 8001 con copia SQLite y almacenamiento temporal propios.
No se modificaron cuentas, expedientes ni documentos de la demostración en 8000.

## Regresión y límites

Django check sin incidencias; makemigrations --check --dry-run sin cambios;
33 pruebas aprobadas; git diff --check limpio. Sin cambios en servicios ni permisos.
Servidor principal reiniciado para recargar plantillas, disponible en 127.0.0.1:8000.
Sin commits, push ni integración; cambios disponibles para revisión local.

Pendiente: Safari/iOS y Android físicos, teclado virtual, selector de archivos y
cámara del dispositivo, lectores de pantalla y zoom de accesibilidad. Estos anchos
son pruebas en Chrome de escritorio, no certificación de dispositivos reales.
