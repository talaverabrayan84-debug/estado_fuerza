# Fase 2: capacitación, bitácora y carga masiva

Esta ampliación sigue los tres módulos de fase 2 del documento de arquitectura. Conserva el expediente, la vigencia de competencias y los permisos de fase 1. No crea un proyecto Supabase ni publica un servicio por sí sola.

## Recorrido de demostración

Ejecuta `Iniciar-Demo.ps1` desde la raíz y abre `http://127.0.0.1:5173`. Los registros son ficticios y se reinician al detener el servicio. No uses información real en la demostración.

1. Entra como Administrador o Gestor de capacitación. En **Calendario de cursos**, registra un curso y programa su sesión con fechas, sede, modalidad y cupo.
2. Abre una sesión e inscribe un elemento del directorio. Puedes actualizar su estado y calificación. El cupo cuenta todas las inscripciones que no estén en baja; no admite nuevas inscripciones una vez ocupado.
3. Entra como Trabajador. Abre **Mi bitácora**, registra un avance y vincúlalo a una sesión en la que estés inscrito, o elige una actividad general.
4. Después de guardar la actividad, adjunta opcionalmente un PDF, PNG o JPG de hasta 2 MB. Se conserva una evidencia por entrada. Los trabajadores solo consultan su información; administración y capacitación pueden revisar el expediente y sus evidencias.
5. Entra como Administrador. En **Carga masiva**, descarga una plantilla Excel o CSV, complétala y revisa el archivo. Comprueba las filas y confirma la carga cuando no existan errores. Descarga el reporte para conservar el resultado.

## Calendario y cursos

Los cursos tienen tipo, fuente de financiamiento, institución, horas y vigencia opcional. Una sesión representa una edición concreta del curso. El calendario muestra todas las sesiones que coinciden con el mes, incluidas las que empiezan antes o terminan después. La agenda permite leerlas sin recorrer la cuadrícula.

El estado usa la fecha actual de Ciudad de México: próximo antes del inicio, en curso entre ambas fechas inclusive y concluido después del término. Los colores son verde, azul y gris, acompañados por texto. El estado de participación de un elemento es independiente: inscrito, en curso, concluido o baja.

Concluir una sesión o registrar una calificación no acredita por sí solo una certificación ni cambia la vigencia de competencias básicas. La evaluación acreditada se captura en el expediente, conservando su historial.

## Reglas de importación

- Destinos habilitados: `personal` y `competencias_basicas`.
- Formatos: CSV UTF-8 (con o sin BOM) o Windows-1252; separador coma, punto y coma o tabulador. Excel `.xlsx` con una sola hoja. No se admiten macros ni fórmulas.
- Máximo 200 filas de datos y 2 MB por archivo. El tamaño descomprimido del libro también está limitado.
- Usa los encabezados de la plantilla sin cambiar sus nombres. CUIP o CURP es obligatorio en cada fila. Guarda los identificadores como texto en Excel para conservar ceros iniciales.
- Personal: nombre, corporación y adscripción son obligatorios. Los nombres de catálogos deben coincidir con registros activos. Las coincidencias por CUIP/CURP actualizan el expediente; sin coincidencia se crea uno. Los campos opcionales vacíos conservan valores existentes; para borrarlos usa la edición individual.
- Competencias: el expediente debe existir. Si se proporcionan ambos identificadores, ambos deben coincidir. La fecha usa `AAAA-MM-DD` o una celda de fecha de Excel. Resultado: `aprobado` o `no_aprobado`.
- Se señalan identificadores repetidos, referencias contradictorias, datos inválidos y evaluaciones duplicadas por persona, fecha y folio.
- La revisión no modifica los expedientes. Se guarda como lote del administrador que la creó y caduca después de una hora.
- La confirmación es transaccional: si una fila entra en conflicto, se revierte todo el lote. Los expedientes modificados después de la revisión requieren revisar de nuevo el archivo. Repetir la confirmación de un lote ya aplicado no duplica registros.
- El reporte CSV distingue filas validadas, procesadas y con error. Los valores exportados que podrían interpretarse como fórmulas se neutralizan.

## Datos y permisos

`002_fase2.sql` agrega `cursos`, `curso_sesiones`, `inscripciones`, `bitacora` y `carga_archivos`. `003_evidencias.sql` agrega `bitacora_evidencias` y el bucket privado de Storage. La ruta del archivo sustituye a una URL pública de evidencia prevista en el documento; el acceso se autoriza al descargar.

La API y PostgreSQL aplican los permisos. Las funciones que guardan inscripciones, bitácoras, importaciones y evidencias validan el rol actual; el navegador no decide quién es propietario de una bitácora. FastAPI conserva el JWT del usuario al llamar a Supabase, sin usar una clave de servicio.

Las operaciones relevantes quedan en la auditoría. Las cargas conservan sus filas de revisión para diagnóstico y trazabilidad; antes de producción se debe acordar con el área responsable su periodo de retención. No se implementa una limpieza automática de esos registros en esta entrega.

## Límites y siguiente etapa

La demo es funcional en memoria. La integración real con Auth, PostgREST y Storage requiere configurar Supabase y ejecutar la aceptación descrita en `CONFIGURACION_SUPABASE.md`. Las pruebas locales de PostgreSQL no sustituyen una prueba concurrente con varias conexiones ni la validación del servicio Storage alojado.

La fase 3 prevista incluye indicadores gráficos, notificaciones automáticas y reportes generales. El modelo especializado de formación inicial y certificaciones distintas de competencias básicas sigue pendiente de implementación y validación operativa.

Referencias técnicas consultadas: [lectura de libros con openpyxl](https://openpyxl.readthedocs.io/en/3.1/tutorial.html), [buckets de Supabase](https://supabase.com/docs/guides/storage/buckets/fundamentals) y [control de acceso a Storage](https://supabase.com/docs/guides/storage/security/access-control).
