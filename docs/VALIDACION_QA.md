# Pruebas y correcciones del 6 de octubre de 2026

La revisión incluyó API, interfaz en navegador con datos ficticios, reglas de negocio y migraciones PostgreSQL. Las correcciones mantienen el contrato de la API y no requieren nuevas migraciones.

## Defectos corregidos

- Los nombres de archivo mayores de 200 caracteres perdían la extensión al recortarse. Se conserva la extensión para aceptar CSV, XLSX y evidencias válidas.
- El historial de evaluaciones de Supabase se truncaba al alcanzar el límite de filas de PostgREST. Se consulta por páginas; la regresión comprueba un historial de 1.105 evaluaciones.
- Los valores numéricos de fecha se convertían silenciosamente en fechas de 1970. Evaluaciones, sesiones, consultas del calendario y actividades ahora aceptan fechas de calendario AAAA-MM-DD válidas. Los CSV con fechas numéricas se señalan como errores de fila.
- No se podía editar un expediente cuando todas las corporaciones estaban inactivas. La edición permite conservar la corporación ya asignada; las altas siguen requiriendo una corporación activa. La consulta fallida de catálogos ofrece reintento.
- En demostración, las evaluaciones del mismo día aparecían con la antigua primero. La evaluación actual y última capturada se muestra antes del histórico.
- En demostración, cargo y grado asignados no aparecían en el expediente. Se resuelven sus nombres desde los catálogos.
- Las fechas de los datos de demostración se recortaban al día 28 aun en meses con 30 o 31 días. Solo se ajusta el día cuando el calendario del año de certificación lo exige.
- Se ajustó el singular de los avisos de un día y se incorporaron las pruebas de la bitácora institucional al comando habitual `npm run test:database`.

## Validación automatizada

- Backend: 60 pruebas correctas, incluidas 17 regresiones de esta revisión.
- Interfaz: seis pruebas del módulo de conexión correctas.
- PostgreSQL local con PGlite: 28 comprobaciones SQL/RLS de fase 1, 39 de fase 2, seed idempotente, cinco estados de vigencia y 43 comprobaciones postmigración.
- Bitácora institucional en PostgreSQL: permisos, fechas, celdas combinadas, auditoría y conflictos de edición correctos.
- TypeScript y compilación de producción Vite: comprobados antes de publicar.

Las dos advertencias de dependencias del cliente de pruebas no provocan fallos. Una prueba introduce deliberadamente una fecha corrupta de Excel; openpyxl la marca como error, la revisión señala la fila y la confirmación la rechaza.

## Recorrido visual local

Se verificaron alta y edición de expediente, búsqueda por CUIP, evaluación aprobada y una segunda no aprobada del mismo día, orden del historial, catálogo de cursos, programación de una sesión, agenda, inscripción, rechazo por cupo agotado y calificación decimal. Capacitación conserva acceso a evaluaciones sin edición de datos personales. Trabajador consulta su expediente, crea y edita su actividad y adjunta evidencia propia. Una importación CSV pasó por revisión, confirmación y búsqueda del expediente guardado.

La edición con corporaciones inactivas y el bloqueo de nuevas altas sin catálogo activo se comprobaron por separado. En FASP se verificaron los estados a tres días y mañana, el singular «Falta 1 día», la recepción completa, la retirada del aviso global y la persistencia al recargar. Las bandas de siete días, tres días, un día, hoy, vencida y recibida están cubiertas por pruebas de API y PostgreSQL. La aceptación pública de las bandas 7/3/1 se había realizado el 5 de octubre, restaurando después los valores del Excel.

## Alcance y límites

Los recorridos de captura de esta revisión usan la demostración local. En el proyecto alojado se habían verificado ingreso administrador, lectura y edición de las bitácoras, persistencia y comparación completa contra el Excel original. La comprobación local de roles usa sesiones de demostración y `auth.uid()` simulado en PostgreSQL; no equivale a una nueva prueba alojada con dos trabajadores reales.

El endpoint de descarga de evidencias conserva los bytes originales y sus restricciones de acceso en las pruebas de API. El navegador integrado no devolvió un evento de descarga para la evidencia PNG; no se afirma que el archivo haya quedado guardado en Descargas. No se ejecutaron pruebas de carga ni una auditoría integral de seguridad o accesibilidad.

## Reproducir

Desde `backend`: `python -m pytest -q`. Desde `frontend`: `npm test`, `npm run test:database` y `npm run build`. Las pruebas no requieren credenciales ni escriben en Supabase alojado.
