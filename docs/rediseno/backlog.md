# Backlog del rediseño

Esta lista propone trabajo técnico; no sustituye su Product Backlog ni inventa ceremonias Scrum realizadas.

## Incremento disponible en la rama

- Registro de aspirante y sesiones; roles internos administrados por personal autorizado.
- Convocatorias y comités configurables desde el administrador.
- Borrador, edición, carga de documentos y envío.
- Evaluación, correcciones, aprobación simple/doble y seguimiento de estados.
- Auditoría persistente, avisos por usuario y exportación CSV.
- Pruebas automatizadas y workflow CI propuesto para PostgreSQL.
- Interfaz responsive sin servicios externos de fuentes o CSS.

## Siguiente incremento prioritario

1. Revisar arquitectura y patrones contra sus documentos y decisiones ya aceptadas.
2. Ejecutar en la Mac M4 y en las computadoras del equipo; resolver integración con `develop`.
3. Asegurar verificación de correo y recuperación de acceso con proveedor real.
4. Precisar documentación obligatoria por convocatoria y revisión documento por documento.
5. Configurar y ejecutar pruebas PostgreSQL, incluidas aprobaciones simultáneas.
6. Preparar pull request y obtener revisión humana de otro integrante.

## Después

- PWA: manifest, iconos y service worker con política explícita para no almacenar expedientes privados en caché.
- Web Push: consentimiento, suscripciones por dispositivo, revocación al cerrar sesión y cola de entrega con reintentos.
- HTTPS y DuckDNS, servidor de aplicación y AWS con límites presupuestarios.
- Pruebas de carga, copias de seguridad y restauración.
- Seguimiento académico, reportes ampliados y exportaciones adicionales según prioridad del Product Owner.
- Pantallas administrativas propias si el administrador Django no cubre la experiencia esperada.

## Definición de terminado propuesta

Criterios de aceptación cumplidos, pruebas y chequeos pasando, revisión de compañero registrada, documentación alineada y demostración aceptada por el Product Owner. Este incremento no se presenta como ya aceptado ni integrado.
