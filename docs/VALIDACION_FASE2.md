# Validación de la fase 2 y preparación de staging

Fecha de revisión: 24 de septiembre de 2026.

Esta revisión distingue tres entornos: demostración local en memoria, migraciones PostgreSQL probadas con PGlite y servicios reales de Supabase/Vercel. Un resultado local no acredita el funcionamiento de un servicio remoto.

## Pruebas automatizadas

Resultados ejecutados de forma independiente por QA sobre los archivos finales entregados por backend y frontend:

| Suite | Resultado |
| --- | --- |
| Backend FastAPI / pytest | 40 pruebas aprobadas |
| SQL/RLS fase 1, PGlite | 28 verificaciones aprobadas |
| SQL/RLS fase 2, PGlite | 39 verificaciones aprobadas |
| Staging, PGlite | Seed idempotente, cinco estados de vigencia y 43 comprobaciones postmigración aprobadas |
| Configuración y cliente frontend / Node | 6 pruebas aprobadas |
| TypeScript + Vite | Compilación de producción aprobada |
| HTTP contra API demo en ejecución | 23 comprobaciones aprobadas |

Pytest emitió dos advertencias de obsolescencia de dependencias de TestClient y una advertencia de caché por permisos locales; no hubo fallos de pruebas. La compilación frontend acredita el código y el empaquetado, no que las variables de un despliegue real estén configuradas.

Comandos reproducibles desde la raíz del proyecto:

```powershell
Set-Location backend
python -m pytest -q
Set-Location ../frontend
npm.cmd test
npm.cmd run test:database
npm.cmd run build
```

## Pruebas de interfaz

La API demo se verificó en `http://127.0.0.1:8000`; el servidor frontend estaba preparado en `http://127.0.0.1:5173`. La automatización de navegador no pudo inicializarse: respondió `Browser is not available: iab` y el inventario devolvió cero navegadores disponibles. Por ello la inspección visual y las interacciones de navegador permanecen pendientes. Las pruebas HTTP no se presentan como pruebas de interfaz.

La matriz y su evidencia actual:

| Flujo | Verificado por API | Pendiente en navegador |
| --- | --- | --- |
| Cursos y sesiones | Alta, programación y consulta de detalle | Formularios, calendario y agenda |
| Inscripciones | Alta con estado/calificación, ocupación y denegación al trabajador | Selección de persona y edición |
| Bitácora | Alta por trabajador vinculada a su inscripción; edición/propiedad cubiertas por pytest | Formulario, edición y consulta visual |
| Evidencia | Adjuntar PDF ficticio, descarga autenticada por staff y rechazo anónimo | Selector de archivo y descarga desde la pantalla |
| CSV y XLSX | Previsualización, confirmación, reporte y rechazo de dos filas duplicadas | Tabla previa, botones, historial y descarga |
| Sesión | Logout invalida ambos tokens de prueba y `/me` responde 401 | Redirección a acceso |
| Diseño adaptable | No aplicable | Pantallas estrechas, desbordamientos y controles |

Se utilizaron exclusivamente personas, cursos y archivos ficticios. Los datos de demostración se pierden al reiniciar el backend. El ejecutor de esta revisión y sus fixtures permanecen en `work/qa-fase2/smoke_local.py` del workspace de desarrollo; se ejecutó con Python del entorno virtual local. Requiere el backend demo activo, `httpx` y los fixtures del mismo directorio; comprueba primero que el endpoint de salud devuelve modo `demo`. Este auxiliar no es una prueba de Supabase real ni forma parte del despliegue.

## Servicios remotos

El proyecto remoto `estado-fuerza-staging` (`oeauqqrjftikgzrwpyrk`) quedó creado en Supabase. El 24 de septiembre de 2026 se ejecutó el paquete de migraciones, el seed ficticio y `verify_staging.sql` desde el editor SQL del proyecto. Supabase devolvió 43 comprobaciones y las 43 resultaron `true`. La revisión cubre tablas y RLS, ausencia de lectura anónima, vistas con `security_invoker`, RPC limitadas a usuarios autenticados, `search_path` fijo en funciones privilegiadas, bucket privado con límites y las tres políticas de evidencias.

Esta comprobación acredita la estructura y los permisos de base de datos instalados. Aún se deben crear las cuentas ficticias de Authentication, vincularlas con `public.usuarios` y ejecutar los recorridos integrados con JWT reales. Vercel todavía requiere el despliegue y la configuración de variables de entorno.
