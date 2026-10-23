# Textos de las convocatorias de demostración

23 de octubre de 2026. Rama `feature/textos-convocatorias`, basada en
`origin/feature/menu-movil` (7fa2c7e); conserva el menú móvil. Cambios guardados
en un commit local, pendientes de publicación. El pie de proyecto universitario y demostración no cambia.

## Descripciones predeterminadas

**Beca de continuidad universitaria**

Promueve la continuidad de los estudios universitarios en Guatemala y el avance
de los estudiantes en su formación académica y profesional.

**Impulso a la educación media**

Busca impulsar la permanencia de los estudiantes en la educación media en Guatemala
y fortalecer su preparación académica para continuar sus estudios y desarrollar sus proyectos de vida.

**Especialización y nuevos horizontes**

Tiene como propósito fomentar la formación de posgrado y la especialización de
estudiantes en Guatemala, para profundizar sus conocimientos y contribuir a su
desarrollo académico y profesional.

No se añaden patrocinadores, beneficios garantizados, criterios de selección,
condiciones, moneda ni periodicidad. Los requisitos, fechas, montos y reglas existentes
permanecen sin cambios.

## Actualización explícita y limitada

`seed_demo` usa los textos nuevos para convocatorias que aún no existen. Ejecutarlo
normalmente conserva las descripciones de las convocatorias ya creadas.

La opción `--actualizar-textos` NO crea usuarios, convocatorias ni comités, y no
requiere DEMO_PASSWORD. Solo sustituye la descripción cuando coinciden exactamente:

- Uno de los tres títulos de demostración.
- Su nivel original: universitario, medio o posgrado.
- El texto anterior completo: «Programa ficticio para apoyar la continuidad académica
  y el desarrollo profesional de estudiantes.»

Solo se actualiza el campo descripcion. Cualquier texto personalizado, vacío,
parecido o extendido queda intacto; también quedan intactos títulos o niveles ajenos.
Repetir la operación no crea duplicados ni modifica descripciones ya actualizadas.
No es una migración automática y no se ejecuta al iniciar el servidor.

Para repetirla EXCLUSIVAMENTE sobre la vista previa independiente ya configurada:

```bash
cd ~/Documents/GuateBecas-integracion
PYTHONPATH="$PWD/.local:$PWD" DJANGO_SETTINGS_MODULE=menu_settings \
  DEBUG=true DB_ENGINE=sqlite .venv/bin/python manage.py seed_demo --actualizar-textos
```

No ejecutar ese comando con otra configuración si se quiere conservar el alcance
sobre el puerto 8002. La configuración y los respaldos de `.local` no se versionan.

## Aplicación y comprobaciones locales

Destino confirmado antes de ejecutar: `.local/menu-demo.sqlite3`, usada por el
servidor independiente del puerto 8002. Se hizo un backup privado previo.
Primera ejecución: 3 descripciones actualizadas. Segunda: 0; permanecen 3 convocatorias.
Se compararon todas las tablas: únicamente cambió descripcion en esas tres filas;
usuarios, contraseñas, expedientes y sus estados permanecieron iguales.

La base original `../GuateBecas/db.sqlite3` del puerto 8000 conservó su SHA-256.
Su expediente 1 permanece aprobado. No se aplicó actualización ni sincronización
sobre ella, y no se reinició ninguno de los servidores.

43 pruebas SQLite aprobadas (39 anteriores + 4 de generación, actualización limitada,
idempotencia y preservación de personalizaciones/campos). El generador repetido
conserva las descripciones personalizadas; la actualización sin filas no crea datos.

Chrome local con viewport de 360 y 390 px: inicio y detalle de las tres convocatorias
(8 combinaciones), sin desbordamiento horizontal ni errores JavaScript. El aviso de
proyecto universitario y entorno de demostración sigue visible en el pie. Se
inspeccionó la captura del detalle de posgrado a 360 px. Evidencia local ignorada:
`.local/textos-evidencias/`. Esta comprobación no acredita otros navegadores físicos.

## Validación manual confirmada por el usuario

El 23 de octubre de 2026, el usuario confirmó que revisó las descripciones desde
su teléfono y que le agradan. Esta confirmación corresponde a los textos de la
vista previa independiente del puerto 8002 y complementa la revisión automatizada
anterior. No se especificaron el dispositivo, navegador ni ancho de pantalla, por
lo que no se atribuye cobertura adicional a modelos o navegadores concretos.
