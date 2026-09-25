# Configuración de Supabase y puesta en marcha

La aplicación está preparada para Supabase. Todavía no se ha creado ni configurado un proyecto real. Completa estos pasos en un proyecto de desarrollo antes de usar datos reales.

## 1 Crear el proyecto

Crea un proyecto de Supabase para desarrollo. Conserva su URL y la clave pública anon o publishable. Guarda la contraseña de la base en tu gestor de contraseñas; la aplicación no la necesita. No coloques la clave `service_role` en el frontend ni en los archivos de esta entrega.

## 2 Aplicar el modelo

Abre el editor SQL del proyecto y ejecuta el archivo completo `supabase/migrations/001_fase1.sql`. Está diseñado para un proyecto vacío y debe ejecutarse una sola vez. Usa la transacción incluida; si ocurre un error, corrígelo antes de continuar. En un proyecto que ya tiene tablas se debe revisar una migración de adaptación.

La migración crea personal, usuarios, competencias, catálogos, configuración, auditoría, RLS y funciones. No crea cuentas ni inserta personal ficticio.

Después ejecuta `supabase/migrations/002_fase2.sql` y `supabase/migrations/003_evidencias.sql`, en ese orden y una sola vez. Si ya aplicaste la fase 1, ejecuta únicamente estas dos migraciones nuevas. No vuelvas a ejecutar `001_fase1.sql` sobre las tablas existentes.

La segunda migración agrega cursos, sesiones, inscripciones, bitácoras, cargas y sus permisos. La tercera usa Supabase Storage y crea el bucket privado `bitacora-evidencias`, con límite de 2 MB y tipos PDF/PNG/JPG, además de las políticas por propietario y personal autorizado. Conserva el bucket privado. La API descarga los archivos con el JWT del usuario y no publica URLs abiertas.

## 3 Cargar catálogos reales

En el editor de tablas o en SQL, agrega las corporaciones, cargos y grados aprobados por el área responsable. Por ejemplo, sustituye el texto antes de ejecutar:

```sql
insert into public.corporaciones(nombre) values ('NOMBRE OFICIAL DE LA CORPORACIÓN');
```

El alta de personal exige una corporación existente. Cargo y grado son opcionales. `adscripcion` conserva texto libre según el diccionario de la fase 1.

## 4 Crear y habilitar cuentas

En Authentication → Users crea las cuentas autorizadas. Deshabilita el registro público si se trata de un sistema interno y configura las políticas de contraseña de tu organización. Crear una cuenta en Auth no le concede acceso al sistema hasta vincularla con `public.usuarios`.

Para el primer administrador, copia su UUID de Auth y reemplaza el marcador:

```sql
insert into public.usuarios(id, rol, activo)
values ('UUID_DEL_USUARIO_DE_AUTH', 'admin', true);
```

Para un gestor:

```sql
insert into public.usuarios(id, rol, activo)
values ('UUID_DEL_USUARIO_DE_AUTH', 'capacitacion', true);
```

Para un trabajador, primero registra su expediente desde la aplicación y luego vincula ambos UUID:

```sql
insert into public.usuarios(id, personal_id, rol, activo)
values ('UUID_DEL_USUARIO_DE_AUTH', 'UUID_DEL_EXPEDIENTE', 'trabajador', true);
```

Cada expediente admite una cuenta vinculada. El navegador no puede cambiar roles ni activar cuentas. Para revocar el acceso, actualiza `usuarios.activo=false` desde el entorno administrativo.

## 5 Configurar las variables

Copia `backend/.env.example` a `backend/.env` y completa:

```dotenv
APP_ENV=development
DEMO_MODE=false
SUPABASE_URL=https://TU_PROYECTO.supabase.co
SUPABASE_ANON_KEY=CLAVE_PUBLICA
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Copia `frontend/.env.example` a `frontend/.env.local` y completa:

```dotenv
VITE_API_URL=http://127.0.0.1:8000/api
VITE_DEMO_MODE=false
VITE_SUPABASE_URL=https://TU_PROYECTO.supabase.co
VITE_SUPABASE_ANON_KEY=CLAVE_PUBLICA
```

La clave pública puede formar parte del frontend. La seguridad de los datos depende de los permisos y las políticas RLS, que se incluyen en la migración. Los archivos `.env` se excluyen de Git. El proceso FastAPI debe iniciarse desde `backend` para cargar el archivo `.env`.

## 6 Iniciar localmente

Detén la demostración antes de usar los mismos puertos. Instala las dependencias según el README. En una terminal situada en `backend`, ejecuta `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`. En otra situada en `frontend`, ejecuta `npm run dev`.

Abre `http://127.0.0.1:5173`, inicia sesión como administrador y captura el primer expediente. Usa una cuenta de trabajador para confirmar que no puede acceder al expediente de otra persona ni registrar evaluaciones.

## 7 Ajustar el umbral de alerta

El valor inicial es 90 días. Para cambiarlo, utiliza el editor SQL con la autorización operativa correspondiente:

```sql
update public.configuracion set dias_alerta = 60 where id = 1;
```

La vista y el panel consultan el mismo valor. Las fechas y el estado se calculan al consultar, sin tareas programadas.

## 8 Preparar Vercel

Esta entrega no publica el sistema. Cuando se decida desplegar, utiliza dos proyectos del mismo repositorio:

- **Frontend:** directorio raíz `frontend`, preset Vite, comando `npm run build`, salida `dist`. Completa las variables `VITE_*` antes de compilar. `VITE_API_URL` debe terminar en `/api` y apuntar al backend público.
- **Backend:** directorio raíz `backend`, FastAPI, punto de entrada `main.py`. Configura `APP_ENV=production`, `DEMO_MODE=false`, URL y clave pública Supabase. `FRONTEND_ORIGINS` debe contener exactamente las URLs HTTPS autorizadas del frontend, separadas por comas.

Supabase debe permitir los orígenes de autenticación de los entornos elegidos. Mantén proyectos separados para desarrollo y producción. No configures cron en esta fase. Verifica el inicio de sesión real, permisos, inserción, renovación, importación y descarga de evidencias después del despliegue. Las cargas están limitadas a 200 filas y 2 MB; valida los tiempos de respuesta y límites del plan elegido antes de trabajar con volúmenes reales.

Prueba el control de cupo con dos peticiones simultáneas para el último lugar. Prueba una carga cuya segunda fila entre en conflicto después de revisar: la primera fila tampoco debe guardarse. Prueba la descarga de una evidencia con su propietario, con capacitación y con un segundo trabajador; este último debe recibir una denegación.

Referencias: [RLS de Supabase](https://supabase.com/docs/guides/database/postgres/row-level-security) y [FastAPI en Vercel](https://vercel.com/docs/frameworks/backend/fastapi).
