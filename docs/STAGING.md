# Entorno de pruebas con Supabase y Vercel

El objetivo es probar el flujo real de autenticación, API y almacenamiento con información ficticia. `DEMO_MODE=false` conecta la aplicación al proyecto de pruebas; `DEMO_MODE=true` corresponde exclusivamente a la demostración local en memoria.

## Orden de preparación

1. Crear el proyecto Supabase `estado-fuerza-staging` en la organización del propietario. Elegir la región Americas y conservar la contraseña de PostgreSQL fuera del repositorio.
2. Mantener habilitada Data API, deshabilitar la concesión automática de permisos a nuevas tablas y habilitar RLS automático. Las migraciones conceden los permisos concretos de la aplicación.
3. Ejecutar `001_fase1.sql`, `002_fase2.sql` y `003_evidencias.sql` en orden, una sola vez. No usar un reinicio de base de datos para actualizar un proyecto existente.
4. Cargar opcionalmente `supabase/seed_staging.sql`, exclusivamente en el entorno de pruebas. El seed no crea cuentas ni contraseñas. Ejecutar `supabase/verify_staging.sql` para comprobar esquema, permisos y configuración de evidencias.
5. Crear cuentas de prueba en Authentication y vincularlas con `public.usuarios`, siguiendo `CONFIGURACION_SUPABASE.md`. Usar un administrador, un gestor y dos trabajadores diferentes para probar aislamiento entre expedientes. Cada trabajador debe vincularse a un expediente ficticio distinto.
6. Guardar las variables de entorno fuera de Git. Verificar inicio de sesión, permisos y persistencia antes de publicar los servicios.
7. Crear un commit revisado, sincronizar el repositorio y conectar los dos proyectos de Vercel descritos abajo. Registrar las URLs reales de despliegue y repetir la aceptación integrada.

## Proyectos Vercel

| Configuración | API | Interfaz |
| --- | --- | --- |
| Nombre sugerido | `estado-fuerza-api-staging` | `estado-fuerza-web-staging` |
| Directorio raíz | `backend` | `frontend` |
| Framework | FastAPI | Vite |
| Punto de entrada / salida | `main.py` exporta `app` | `npm run build`, salida `dist` |
| Persistencia | Supabase | Supabase por la API |

Despliegues actuales:

- API: `https://estado-fuerza-api-staging.vercel.app`
- Interfaz: `https://estado-fuerza-web-staging.vercel.app`
- La API tiene `FRONTEND_ORIGINS` configurado con el dominio estable de la interfaz y fue redeployada después del cambio.

FastAPI utiliza un punto de entrada soportado por Vercel. No hay un servidor persistente ni almacenamiento local durable para datos de negocio. Consulta la [documentación de FastAPI en Vercel](https://vercel.com/docs/frameworks/backend/fastapi).

Configurar en la API:

```dotenv
APP_ENV=production
DEMO_MODE=false
SUPABASE_URL=https://REFERENCIA_REAL.supabase.co
SUPABASE_ANON_KEY=CLAVE_PUBLICA_DEL_PROYECTO_DE_PRUEBAS
FRONTEND_ORIGINS=https://DOMINIO_REAL_DEL_FRONTEND
```

Configurar en la interfaz antes de compilar:

```dotenv
VITE_DEMO_MODE=false
VITE_API_URL=https://DOMINIO_REAL_DE_LA_API/api
VITE_SUPABASE_URL=https://REFERENCIA_REAL.supabase.co
VITE_SUPABASE_ANON_KEY=CLAVE_PUBLICA_DEL_PROYECTO_DE_PRUEBAS
```

Los marcadores anteriores son instrucciones, no valores utilizables. Registrar el dominio estable del frontend en Auth de Supabase. CORS debe contener los orígenes exactos autorizados. Si cambia la URL del frontend, actualizar el backend; si cambia la API, reconstruir el frontend. No agregar comodines para aceptar cualquier origen.

La contraseña PostgreSQL, claves `service_role`, claves `sb_secret_`, tokens de administración y contraseñas de usuarios no forman parte del frontend ni del código. La aplicación usa la clave pública con el JWT de cada usuario. Evitar incluir `.env`, archivos temporales y registros de ejecución en Git.

## Aceptación integrada

- `/api/health` responde con `mode: supabase`; no basta para demostrar acceso a tablas, por lo que deben completarse los pasos siguientes.
- El administrador registra un expediente ficticio y lo encuentra después de reiniciar o volver a desplegar la API.
- Una renovación conserva el historial y calcula la vigencia esperada.
- Dos inscripciones simultáneas al último lugar disponible producen una sola inscripción activa adicional.
- El trabajador captura una bitácora propia; otro trabajador no puede leerla, modificarla ni descargar su evidencia, incluso usando una URL conocida.
- La evidencia se conserva en un bucket privado y puede descargarla su propietario y capacitación.
- Una carga CSV y otra XLSX muestran revisión antes de escribir. Un conflicto durante la confirmación revierte todo el lote. Un reintento de confirmación no duplica filas.
- Una cuenta deshabilitada pierde acceso. Un cierre de sesión elimina la sesión visible; una respuesta anterior no vuelve a mostrar el perfil.

Conservar evidencia de cada resultado y distinguir los fallos de configuración de los defectos de aplicación. Las pruebas PostgreSQL locales usan PGlite y no sustituyen estos recorridos contra Supabase y Vercel.

La separación de entornos mantiene los datos de prueba fuera de una futura base operativa. Referencia: [gestión de entornos de Supabase](https://supabase.com/docs/guides/deployment/managing-environments).

## Estado actual

El 5 de octubre de 2026 el propietario creó `estado-fuerza-2026` (`hchpnsmxipnmwtwmrvjm`). Se aplicaron las migraciones 001 a 004 y se cargaron las hojas del Excel. La comparación completa devolvió `true` para FASP y FOFISP; también pasaron las 43 comprobaciones de estructura y permisos y la comprobación de RLS y ausencia de acceso anónimo a la nueva bitácora. Esta instalación no migra usuarios, expedientes ni evidencias del proyecto anterior.

En Production de ambos proyectos Vercel se guardaron las nuevas parejas de conexión: `SUPABASE_PROJECT_URL` / `SUPABASE_PUBLISHABLE_KEY` para la API y `VITE_SUPABASE_PROJECT_URL` / `VITE_SUPABASE_PUBLISHABLE_KEY` para la interfaz. Vercel rechazó editar las variables `VITE_*` antiguas guardadas como Secret; las nuevas variables se guardan como Config y contienen solo la URL y clave pública. El código da prioridad a cada pareja nueva y no mezcla su URL con la clave anterior. Sin esa pareja se conserva la configuración anterior, incluida Preview. No se ha realizado un nuevo despliegue.

El propietario creó la cuenta ficticia `admin.pruebas@example.test` y autorizó habilitarla como administradora. Se verificó su vínculo activo con `public.usuarios`; el inicio de sesión desde una interfaz local conectada a la base nueva funcionó, y ambas hojas y las alertas se cargaron desde Supabase. La actualización local pasó 43 pruebas del backend, TypeScript y compilación Vite.

El repositorio anterior `talaverabrayan84-debug/estado-fuerza` no es accesible desde las herramientas de Git y el conector; Vercel conserva acceso a ese repositorio privado. El propietario autorizó usar `talaverabrayan84-debug/estado_fuerza`; se actualizó el remoto local. El conector permite leerlo pero rechazó la escritura con HTTP 403 («Resource not accessible by integration»). Git sigue requiriendo completar la autenticación fuera del entorno de herramientas. Pendientes: publicar la rama `fase-2`, conectar los dos proyectos Vercel al repositorio nuevo y validar el despliegue desde la URL pública.

El 5 de octubre de 2026 se reactivó el proyecto que estaba pausado y se aplicó `004_bitacora_fondos.sql`. Se cargaron las hojas FASP y FOFISP del archivo proporcionado y la comparación completa de los valores guardados devolvió `true` para ambos fondos. La publicación del código actualizado en Vercel queda pendiente de completar el acceso de Git a GitHub y el autenticador solicitado por Vercel.

El 24 de septiembre de 2026 se aplicaron las tres migraciones y el seed ficticio en `estado-fuerza-staging` (`oeauqqrjftikgzrwpyrk`). Las 43 comprobaciones de `verify_staging.sql` devolvieron `true`. Las siete cuentas ficticias de Authentication ya están creadas, confirmadas y vinculadas con `public.usuarios`. La API y la interfaz están desplegadas en Vercel con `DEMO_MODE=false`; falta ejecutar la aceptación integrada desde la URL pública y configurar el dominio estable en la sección URL Configuration de Supabase Auth si se desea probar redirecciones OAuth.
