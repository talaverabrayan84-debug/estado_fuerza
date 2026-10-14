# Cargas normalizadas de XLSX y CSV

Estado de fuerza puede anexar expedientes, actualizar los existentes o combinar ambas operaciones. La identidad se resuelve por CUIP o CURP; no se usa el nombre para deduplicar. Competencias básicas anexa evaluaciones y conserva el historial: no sobrescribe evaluaciones ya existentes.

## Recorrido

1. Seleccionar destino, archivo y operación. Pulsar **Analizar archivo**. El análisis no crea un lote ni escribe expedientes.
2. Para un libro con varias hojas, seleccionar expresamente una hoja y volver a analizar. Se puede ajustar la fila de encabezados; la detección automática examina las primeras diez filas con datos.
3. Revisar las columnas sugeridas o relacionarlas manualmente. Una columna solo puede alimentar un campo. Coincidencias duplicadas requieren selección; columnas sin relación se muestran como omitidas. La muestra permite comprobar los valores originales.
4. Pulsar **Revisar cambios**. Se comparan los valores normalizados con la base actual y se muestra cada valor anterior y nuevo. Revisar errores, altas y actualizaciones.
5. Confirmar el lote completo. Los conflictos concurrentes revierten la transacción; reintentar una confirmación exitosa no duplica registros. La revisión caduca a la hora. El historial y el reporte CSV conservan normalizados, cambios, avisos y operación.

## Normalización y límites

- Encabezados: mayúsculas, acentos y separadores; alias explícitos como `Nombre del elemento`, `Unidad de adscripción` y `Fecha de certificación`. Encabezados desconocidos pueden relacionarse manualmente. No se inventan campos o valores faltantes.
- Texto: espacios y Unicode; identificadores: mayúsculas. Los espacios internos de identificadores siguen siendo inválidos. CUIP/CURP contradictorios y duplicados se marcan como errores.
- Catálogos: coincidencia de nombre normalizado, sin aproximaciones; debe existir exactamente un registro activo. No se crean catálogos durante la importación.
- Sexo: H/hombre/masculino y M/mujer/femenino. Resultado: aprobado/no aprobado. Estatus: activo, baja, comisionado o licencia. Valores desconocidos se rechazan.
- Fechas: AAAA-MM-DD, DD/MM/AAAA o DD-MM-AAAA; las barras y guiones en formatos no ISO se interpretan expresamente como día/mes/año. Las fechas nativas de Excel se convierten a ISO. No se convierten números CSV ni timestamps en fechas.
- Identificadores numéricos de Excel: se conservan ceros si el formato explícito es una secuencia de ceros, como `000000`. Se rechazan números con 16 o más dígitos para evitar importar valores cuya precisión Excel pudo perder. Cuando el archivo ya perdió ceros sin un formato que los conserve, no se reconstruyen: usar texto en origen.
- Altas: CUIP o CURP, nombre completo, corporación y adscripción obligatorios. Actualizaciones: identificador y campos que se desea cambiar; vacíos y ausencias conservan valores existentes, incluidos los campos obligatorios. Un identificador ya asignado que contradice el archivo no se sobrescribe. Expedientes sin cambios de contenido se señalan con un aviso.
- Modo anexar rechaza expedientes existentes. Modo actualizar rechaza identificadores sin expediente. Los errores bloquean el lote entero, sin omitirlos silenciosamente.
- Se conservan los límites de 2 MB, 20 columnas y 200 registros. En XLSX las filas físicas, incluidos títulos y encabezados, deben estar entre 1 y 201. En CSV se admiten coma, punto y coma o tabulación, UTF-8 y Windows-1252. Se rechazan macros, fórmulas, archivos dañados y libros cuya expansión excede los límites. Las columnas omitidas tampoco admiten prefijos de fórmula.

## API y compatibilidad

`POST /api/carga-masiva/analizar` recibe `destino`, `archivo`, `hoja` opcional y `fila_encabezado` opcional. Devuelve hojas, fila, columnas sugeridas y muestra; solo administradores.

`POST /api/carga-masiva/previsualizar` añade `modo` (`combinar`, `anexar`, `actualizar`), `hoja`, `fila_encabezado` y `mapeo`, un objeto JSON de campo a índice de columna comenzando en cero. El modo por defecto y los encabezados originales siguen siendo compatibles. Ejemplo: `{"cuip":0,"adscripcion":2}`.

Los detalles del análisis se almacenan en el JSON `filas` existente. No se necesita migración de base de datos. Las celdas de muestra de columnas omitidas no se persisten. El reporte añade columnas después de las cinco originales. Confirmación, permisos, RLS, auditoría y control de versión de expedientes mantienen su contrato.

## Validación de esta entrega

- Backend: 92 pruebas aprobadas, incluidas 32 nuevas variantes de importación y actualización parcial.
- Frontend: compilación TypeScript/Vite y seis pruebas del cliente API aprobadas.
- SQL local con PGlite: permisos, transacciones, conflictos, reintentos y persistencia de metadatos. Estas pruebas no sustituyen el recorrido sobre Supabase alojado.
- No se ingresó a una sesión administrativa del sitio, no se probaron cargas sobre su base alojada y no se publicó esta versión durante la preparación.

Publicar API e interfaz del mismo cambio sobre los proyectos Vercel existentes; no cambiar el proyecto Supabase ni ejecutar seeds. Tras publicar, verificar con un archivo ficticio y una sesión administradora: analizar, ajustar columnas, revisar y confirmar una alta y una actualización; comprobar su persistencia y el reporte.
