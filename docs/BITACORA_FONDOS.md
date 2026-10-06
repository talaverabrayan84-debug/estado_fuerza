# Bitácora institucional FASP y FOFISP

La ruta `/bitacora-fondos` permite a administración y capacitación editar las hojas FASP y FOFISP del archivo de referencia. Conserva sus encabezados, colores, anchos relativos, celdas combinadas y agrupaciones. La bitácora individual del trabajador sigue disponible en su expediente.

La fecha límite UMS se lee de J en FASP y de I en FOFISP. Cada celda combinada de entrega representa un solo seguimiento, aunque incluya varios grupos o el curso y su evaluación. Las fechas de término del curso y de validación no disparan estos avisos.

Los avisos internos se calculan con el calendario de America/Mexico_City. Se muestran desde 7 días antes, cambian de prioridad a 3 y 1 días, e incluyen el día de entrega y las entregas vencidas. El aviso general y la tabla se actualizan cada minuto mientras el sistema está abierto y al recuperar el foco. También se actualizan al guardar. No requieren un servicio cron ni envían correos o mensajes externos.

La recepción completa con fecha, la marca ENTREGADO en la fecha de entrega o una marca exacta ✔/✓ en ENTREGABLES POR PARTE DE LA UMS cierran el aviso. Texto de entrega parcial conserva el aviso. Para reabrir se elimina la fecha de recepción y las marcas de entrega existentes. N/A o una fecha vacía aparecen como sin fecha.

## Instalación en el entorno existente

1. Aplicar `supabase/migrations/004_bitacora_fondos.sql` una vez, después de las migraciones anteriores. Crea dos hojas vacías con sus celdas editables y permisos. No modifica el personal, las inscripciones ni la bitácora individual.
2. Cargar los valores del archivo proporcionado mediante el SQL de carga inicial entregado por separado. Solo llena hojas vacías, conservando cualquier captura que ya exista. Los datos reales de referencia no se guardan en Git ni se mezclan con la demostración ficticia.
3. Publicar backend y frontend en sus proyectos Vercel existentes. No se agregan variables de entorno ni claves privilegiadas.

Las escrituras usan JWT de usuario, validación en API y función SQL con comprobación de rol. La función conserva la estructura, aplica cambios a una celda, exige la revisión vigente y registra auditoría. Las cuentas de trabajador, anónimas y deshabilitadas carecen de acceso a esta bitácora institucional. La recepción no admite fechas futuras.

## Validación

Se agregó cobertura de plazos 8/7/4/3/2/1/0/-1 días, fechas faltantes e inválidas, recepción parcial/completa, reapertura, agrupaciones, permisos y conflictos de edición. `backend/tests/test_funding.py` prueba API y cálculo. `supabase/tests/funding.mjs` prueba permisos reales de PostgreSQL y auditoría con PGlite. El formato se revisa en navegador para ambos fondos.
