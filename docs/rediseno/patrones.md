# Patrones implementados y justificación inicial

No basta contar clases del framework: estos seis patrones están expresados en código propio. La justificación y el uso deben revisarse en equipo antes de presentarlos como decisiones definitivas.

| Categoría | Patrón | Implementación | Problema resuelto | Alternativa y motivo de elección | Ventaja y costo |
|---|---|---|---|---|---|
| Creacional | Builder | `ReporteBuilder` en `solicitudes/reportes.py` | Componer secciones de un reporte autorizado | Constructor con muchos indicadores; se eligieron pasos explícitos de identificación y seguimiento | Reutiliza secciones; añade clases para un reporte inicialmente pequeño |
| Creacional | Factory Method | `Exportador.crear_documento`, `ExportadorCSV` y `DocumentoCSV` | Separar preparación del reporte de la creación de su representación | Instanciar el CSV directamente en la vista; el creador deja extender la salida sin cambiar el flujo de exportación | Producto sustituible; hoy existe un solo formato y se debe justificar la extensión prevista |
| Estructural | Facade | `ExpedienteFacade` en `solicitudes/services.py` | Coordinar permisos, reglas, persistencia y efectos del expediente | Repetir coordinación en cada vista; se elige una entrada de aplicación por operación | Uso simple desde HTTP y pruebas; requiere evitar que la fachada concentre nuevas responsabilidades ajenas |
| Estructural | Adapter | `DjangoStorageAdapter` en `solicitudes/storage.py` | Abrir archivos mediante un contrato de dominio sin rutas locales en la vista | Acceso directo al filesystem; se adapta Django Storage a `abrir(referencia)` | Facilita almacenamiento alternativo; la sustitución por otro backend aún requiere configuración y pruebas |
| Comportamiento | State | `EstadoSolicitud` y estados concretos en `solicitudes/patterns.py` | Evitar transiciones arbitrarias por cadena recibida de un formulario | Condicionales distribuidos o tabla de transiciones global; se agrupan acciones válidas por estado | Transiciones explícitas y extensibles; la política del monto queda en el servicio, no duplicada en cada estado |
| Comportamiento | Observer | `GestorObservadores`, `AuditoriaObserver`, `NotificacionObserver` | Reaccionar a un evento con auditoría y notificaciones independientes | Envíos o impresiones desde `save`; se notifica desde una operación atómica explícita | Efectos testeables y persistentes; no es una cola durable ni un servicio push |

Los tests de flujo verifican consecuencias de State, Facade y Observer. La exportación CSV verifica Builder y Factory Method, incluyendo neutralización de fórmulas. La descarga autenticada verifica el Adapter. La revisión de código debe contrastar estos nombres con la definición formal de cada patrón y las necesidades del equipo.

## Contraste con los antecedentes del repositorio

Revisión de los cuatro `docs/Anexo5_*.drawio`: contienen dominio, casos de uso,
componentes y modelo relacional, pero no justifican estos seis patrones.
Por tanto, el conteo 2 creacionales + 2 estructurales + 2 de comportamiento se
sustenta en el código y esta tabla; no implica aprobación académica previa.

- Clases: `Usuario` abstracto y subtipos se implementan con User + Perfil/rol;
  Solicitud, Documento, Convocatoria, Comité y Evaluación sí tienen equivalentes.
  El reporte se construye al exportar, sin entidad persistente Reporte.
- Estados: el anexo enumera EN_PROCESO/EVALUADA/APROBADA/RECHAZADA/CANCELADA;
  State incorpora borrador, revisión, correcciones, segunda aprobación y seguimiento.
  Cancelación aún no está implementada. Las enumeraciones del anexo no constituyen
  por sí solas una implementación del patrón State.
- Componentes: el anexo propone Angular + ASP.NET + EF Core + JWT; esta rama usa
  templates Django, sesiones, fachada de servicios y ORM. Mantiene separación de
  responsabilidades, pero requiere actualizar y aprobar el diagrama tecnológico.
- Datos: el modelo relacional propone SQL Server y el de componentes PostgreSQL.
  Esta demostración usa SQLite; PostgreSQL compartido sigue pendiente.
- Casos de uso: editar y evaluar tienen soporte; cancelar, gestión completa del
  perfil y asignación individual a comité quedan fuera del incremento. El comité
  actual se vincula a convocatoria. El aprobador es un rol explícito adicional.

Builder y Factory Method son implementaciones pequeñas y verificables; un solo
formato CSV limita su utilidad actual. Adapter adapta el contrato Storage de Django,
no demuestra todavía integración con S3. Facade coordina transacciones, State
valida transiciones y Observer persiste auditoría y avisos internos. La distinción
de dos aprobadores y el umbral estricto >10000 están en el servicio de negocio.
Moneda, periodicidad y aceptación de estos cambios requieren decisión del equipo.
El backlog es una propuesta: no acredita ceremonias ni sprints Scrum realizados.
