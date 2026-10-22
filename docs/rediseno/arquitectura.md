# Decisión de arquitectura · Rediseño BecaNet

Estado: propuesta implementada en una rama, pendiente de revisión del equipo y del Product Owner. Los diagramas originales de `docs/` permanecen como antecedentes y deben contrastarse con este diseño; no se afirma que ya estén sincronizados.

## Problema y decisión

Gestionar un expediente con varios actores, reglas de monto, cambios de estado, archivos privados y trazabilidad, sin duplicar esas reglas en las pantallas. Se elige un monolito modular Django, con presentación en templates, servicios de aplicación, objetos de dominio para estados y persistencia mediante ORM. PostgreSQL es el motor previsto para el entorno compartido; SQLite simplifica la primera prueba local.

Frente a microservicios, reduce despliegues, conexiones y coordinación de transacciones para un equipo universitario. A cambio, los módulos se despliegan juntos. Frente a colocar toda la lógica en vistas o modelos, la fachada ofrece un punto verificable de permisos y cambios del expediente.

## Reglas implementadas

- Un expediente por cuenta y convocatoria, con restricción de base de datos.
- Solo se crean y envían solicitudes en convocatorias publicadas y abiertas.
- Monto positivo, sin exceder el máximo de la convocatoria.
- Borrador → enviada → revisión → aprobada/rechazada/correcciones.
- Correcciones → enviada; las evaluaciones previas se conservan, pero pierden vigencia.
- Para aprobar se necesita al menos una evaluación vigente.
- Si monto > 10000: revisión → segunda aprobación → aprobada.
- La segunda aprobación la realiza una cuenta distinta; restricción única por solicitud y aprobador.
- Aprobada → activa → completada permite seguimiento básico, sin simular pagos.
- Evaluadores acceden por pertenencia a comités de la convocatoria.
- El aspirante consulta sus propios expedientes; no puede aprobar ni evaluar.
- Decisión, estado, auditoría y avisos se guardan dentro de `transaction.atomic`.
- `select_for_update` protege la fila en PostgreSQL; SQLite no ofrece esa garantía.
- Auditoría y decisiones son de solo lectura desde el administrador. No se garantiza inmutabilidad frente a acceso directo a la base.

## Archivos

Se almacenan fuera de `static`, con descarga mediante vista autenticada. Validación de tamaño, extensión y firma básica de PDF o decodificación de imagen; descarga como adjunto. Esto no equivale a análisis antimalware ni validación exhaustiva de PDF. El Storage Adapter permite cambiar el almacenamiento sin modificar la vista de descarga.

## SOLID

Las vistas traducen solicitudes HTTP; la fachada coordina operaciones; los objetos State validan transiciones; los observadores guardan efectos; los modelos describen persistencia. Se pueden añadir observadores y productos de exportación sin editar las vistas. No se agregan capas de repositorio vacías alrededor del ORM. Los observadores usan un contrato pequeño (`actualizar(evento)`).

## Pendientes de validación con el Product Owner

1. Moneda y periodicidad del monto de 10000: total de beca, anual o mensual.
2. Quién puede dar cada aprobación y si existe aprobación colegiada por votos.
3. Documentos obligatorios específicos: la versión inicial exige al menos uno, sin afirmar que cumple todos los requisitos particulares.
4. Regla de puntaje, criterios ponderados y tratamiento de empates.
5. Qué sucede al corregir después del cierre de convocatoria.
6. Seguimiento académico más allá del estado de la beca.
7. Reglas adicionales de identidad, menores de edad y verificación de correo.

## Notificaciones futuras

Hoy se guardan avisos internos por destinatario. Web Push se implementará con suscripciones por cuenta/dispositivo y una bandeja de entrega con reintentos posterior al commit. La caída del proveedor push no debe revertir una aprobación ni ser equivalente a una entrega confirmada al dispositivo.
