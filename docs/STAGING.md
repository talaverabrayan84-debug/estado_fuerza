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

El 24 de septiembre de 2026 se aplicaron las tres migraciones y el seed ficticio en `estado-fuerza-staging` (`oeauqqrjftikgzrwpyrk`). Las 43 comprobaciones de `verify_staging.sql` devolvieron `true`. El siguiente paso es crear las cuentas ficticias de Authentication y vincularlas con `public.usuarios` antes de configurar Vercel.
