# Revisión de seguridad — Fase 2

Fecha de revalidación: 24 de septiembre de 2026. Revisión independiente del agente de seguridad sénior sobre la copia local. Corresponde al código en desarrollo; no es una certificación ni una validación de un despliegue Supabase real.

## Hallazgo corregido y revalidado localmente

**SEG-01 · P2 · El límite del archivo se aplicaba después de recibir el multipart.**

Ubicaciones al revisar: `backend/app/training_routes.py:98`, `backend/app/training_routes.py:101`, `backend/app/evidence.py:34`, `backend/app/evidence.py:39` y `backend/app/main.py:26`.

Las rutas usan `UploadFile`; FastAPI/Starlette analiza el multipart antes de ejecutar el control de rol y la lectura limitada del archivo. El middleware existente solamente añadía cabeceras. Por ello, el límite de 2 MB dentro de la función no impedía escribir un cuerpo mayor en el archivo temporal del parser.

Reproducción local no destructiva: instrumentar en memoria `starlette.formparsers.SpooledTemporaryFile.write`, enviar mediante `TestClient` un archivo CSV de 3 MiB a `POST /api/carga-masiva/previsualizar` sin cabecera de autorización y contar los bytes escritos. Resultado observado: `status=401`, `bytes_spooled_before_auth=3145728`. No se guardó una importación ni se modificaron expedientes. La escritura temporal ocurrió antes del rechazo de autenticación.

Impacto: un cliente sin sesión puede consumir disco y trabajo del parser enviando archivos grandes. La prueba confirma el procesamiento previo al rechazo; no se realizó una prueba de agotamiento de recursos.

Corrección verificada: `backend/app/core/upload_limits.py` incorpora un middleware ASGI antes del parser, instalado en `main.py`. Rechaza la longitud declarada superior a 3 MiB y cuenta los bytes reales para cuerpos sin longitud conocida o declarada incorrectamente. El archivo individual mantiene su límite de 2 MiB. La regresión `test_upload_limits.py` comprueba ambas rutas de carga anónima: con longitud excesiva no se crea el archivo temporal; sin longitud conocida se detiene la lectura y se cierran los archivos temporales. Ambas pruebas pasaron el 22 de septiembre. **SEG-01 cerrado para la implementación local comprobada.** La prueba no mide límites ni comportamiento de transporte del proveedor de despliegue.

## Observación de frontend atendida en el código

**SEG-02 · P2 · Respuesta de perfil anterior al cierre de sesión.** En la versión inicial de `frontend/src/App.tsx`, una petición pendiente a `/me` podía resolver después de `SIGNED_OUT` y ejecutar `setUser` con el perfil anterior. Esto afecta el estado visible de la interfaz; no demuestra acceso adicional al servidor, que sigue verificando JWT y RLS.

Se comunicó la secuencia al responsable frontend. En la revisión posterior de `App.tsx:26`, `App.tsx:28` y `App.tsx:31` ya existe un contador `authGeneration`: las respuestas de generaciones anteriores se ignoran y el cierre de sesión invalida la generación. **Corrección observada por lectura del código; reproducción de la carrera en navegador y prueba de regresión pendientes de QA.**

Revalidación del 22 de septiembre: el contador permanece en el código revisado. Además, la implementación instalada de `@supabase/auth-js`, `GoTrueClient.ts`, método `_signOut`, elimina la sesión local incluso ante un error de la solicitud remota de cierre; una sospecha inicial sobre ese caso se descartó después de revisar la dependencia. Esto no demuestra revocación inmediata de un JWT ya emitido ni sustituye la prueba de carrera en la interfaz.

Revalidación del 24 de septiembre: las seis pruebas automatizadas del frontend pasan, pero cubren configuración y transporte en `api.ts`; ninguna reproduce la carrera de perfil/cierre de sesión en `App.tsx`. **SEG-02 continúa corregido por lectura del código, con validación específica de interfaz pendiente de QA.** No se atribuye a esas seis pruebas una cobertura que no tienen.

## Controles revisados y evidencia local

- Los repositorios Supabase envían el JWT del solicitante y la clave pública; `profile()` consulta Auth y exige una cuenta habilitada. Las funciones privadas de identidad consultan usuarios activos. No se encontró un bypass simple de usuario desactivado en la lectura de las políticas de las migraciones 001–003.
- Las RPC de escritura usan `SECURITY DEFINER` con `search_path` vacío, objetos cualificados, restricciones de rol e identidad derivada de la sesión. El trabajador no puede elegir el propietario de una entrada de bitácora. Las vistas sensibles usan `security_invoker`.
- La carga masiva se limita al administrador y al propietario del lote. La confirmación bloquea el lote, admite reintentos, verifica caducidad y versión del expediente y aplica los cambios dentro de una transacción. La prueba SQL verifica rollback del lote cuando una fila entra en conflicto.
- El bucket de evidencias se declara privado. Las políticas comprueban la relación entre persona, bitácora y ruta; otro trabajador no puede leer el objeto o sus metadatos. La vinculación de una evidencia requiere un objeto existente y una entrada propia. No hay URLs públicas de evidencia en el frontend.
- Las descargas pasan por una petición autenticada y se entregan como adjuntos; la API añade `nosniff` y `no-store`. React presenta nombres, descripciones y errores como texto, sin inserción de HTML arbitrario en las pantallas revisadas.
- La importación conserva fórmulas como texto y las rechaza; el reporte CSV protege las celdas variables contra fórmulas al abrirlo en una hoja de cálculo. Hay límites de archivo, filas y tamaño declarado del ZIP, además de `defusedxml`. El código actual valida las coordenadas del XML de la hoja, sin confiar únicamente en las dimensiones declaradas por el libro; las regresiones incluidas en `test_phase2.py` pasaron en esta revalidación.
- La búsqueda local acotada de patrones de claves privadas, tokens GitHub y claves secretas no encontró credenciales reales en los archivos fuente revisados. El texto `service_role` aparece también en las nuevas validaciones preventivas y sus datos de prueba sintéticos. Esta búsqueda no equivale a una auditoría completa del historial Git o de archivos externos.

Ejecutado por seguridad el 22 de septiembre:

1. `node supabase/tests/phase2.mjs`: **39 comprobaciones correctas**, incluidas RLS de trabajador, evidencia ajena, usuario desactivado, cupos, confirmación idempotente y rollback.
2. Desde `backend`, usando el intérprete `work/.venv/Scripts/python.exe`: `python -m pytest tests/test_upload_limits.py tests/test_phase2.py -q -p no:cacheprovider`: **15 pruebas correctas**, incluidos los dos casos del límite de transporte. Se observaron dos avisos de deprecación del entorno de pruebas; no fallaron las pruebas.
3. Lectura de migraciones 001–003, configuración, repositorios, rutas de evidencia y autenticación de frontend. La reproducción inicial de SEG-01 descrita arriba es evidencia histórica del 15 de septiembre, no el comportamiento actual.

Ejecutado por seguridad el 24 de septiembre:

1. Desde `backend`, con el mismo intérprete: `python -m pytest -q -p no:cacheprovider`: **40 pruebas correctas**, incluidos límites de carga y las cinco pruebas de `test_staging_config.py`. Persisten los dos avisos de deprecación, sin fallos. SEG-01 permanece cerrado localmente.
2. Desde `frontend`: `npm test`: **6 pruebas correctas**, incluidas prevención de claves privilegiadas, transmisión del JWT de usuario, configuración incompleta, restricción del modo demo, multipart y errores/cancelación.
3. Revisión de SQL final: el diff de la migración 001 añade únicamente el permiso explícito `USAGE` sobre `public` para `authenticated` y su comentario; no añade permisos de tabla ni desactiva RLS. Las migraciones 002 y 003 conservan la lógica revisada. `seed_staging.sql` inserta datos sintéticos con `ON CONFLICT DO NOTHING`, no crea cuentas Auth ni contraseñas, no modifica `usuarios`, políticas o permisos y no crea objetos Storage. Esta comprobación es lectura local; no demuestra aplicación remota del seed.

## Preparación del entorno simulado

La copia revisada separa el modo de demostración del acceso Supabase: `DEMO_MODE=true` se rechaza fuera de desarrollo local y cuando existe `VERCEL`. Cada operación autenticada consulta Auth y el perfil habilitado, y transmite el JWT del usuario a PostgREST y Storage. Deben configurarse `DEMO_MODE=false` y `VITE_DEMO_MODE=false` para el entorno compartido, claves públicas y orígenes concretos de frontend.

La mejora preventiva está **implementada y probada**: `Settings.validate()` rechaza claves `sb_secret_` y JWT cuyo payload declara `role=service_role`. `test_staging_config.py` verifica ambos rechazos, acepta las clases públicas anon/publishable y rechaza demo en Vercel; sus cinco casos pasan dentro de la suite de 40 pruebas. El frontend también rechaza ambas clases privilegiadas antes de crear el cliente, con regresiones aprobadas. La inspección del payload identifica una configuración equivocada; no valida la firma del JWT ni reemplaza la autenticación que realiza Supabase Auth. No se encontró una clave privilegiada real en las fuentes revisadas.

Un usuario desactivado todavía puede leer su propio registro de `usuarios` por la política `usuario_propio`; esto permite conocer su estado y no le concede lectura de expedientes o permisos de escritura. Las funciones privadas de identidad devuelven valores únicamente para usuarios activos. La primera habilitación de roles debe hacerse mediante administración controlada, porque el cliente no tiene permisos de escritura sobre `usuarios`. No debe otorgarse ese permiso para facilitar las pruebas.

## Límites y condiciones de cierre

Las pruebas SQL usan PGlite con `auth.uid()` y tablas Storage simuladas. No prueban el servicio HTTP real de Supabase Storage, la configuración de un proyecto, políticas adicionales ya instaladas, revocación real de tokens, límites del proveedor ni concurrencia entre procesos. Las pruebas HTTP de fase 2 ejecutadas usan el repositorio de demostración.

La validación de evidencias comprueba extensión, firma inicial y tamaño; no valida integralmente un PDF o una imagen ni analiza malware. Las restricciones de MIME del bucket no equivalen a esa validación. No se ha afirmado que los archivos aportados sean inocuos.

Pendiente: regresión del cierre de sesión en la interfaz y comprobación de configuración del despliegue. Para validar el proyecto Supabase real deben probarse usuarios ficticios admin, capacitación y dos trabajadores, incluyendo acceso directo a las APIs públicas, rechazo de rol insuficiente, lectura de expediente/evidencia ajenos y rechazo del usuario desactivado. Confirmar también bucket privado, ausencia de políticas adicionales permisivas, registro público deshabilitado si solo se habilitarán cuentas administradas y orígenes/URLs de retorno definidos para el entorno. Estas verificaciones remotas no fueron ejecutadas por este agente y no se declaran aprobadas. No se requieren credenciales dentro del repositorio.
