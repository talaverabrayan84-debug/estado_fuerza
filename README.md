# Sistema de Gestión del Estado de Fuerza

Primera implementación de la fase 1 definida en `Arquitectura_Sistema_Estado_de_Fuerza.docx`, versión 1.0. Incluye React 18 + TypeScript + Tailwind, FastAPI y una migración PostgreSQL para Supabase.

La demostración local permite recorrer los tres perfiles y probar el flujo completo con datos ficticios. La conexión de producción está implementada, pero requiere crear el proyecto de Supabase, aplicar la migración, cargar los catálogos y habilitar las cuentas. No se ha desplegado en internet.

## Funciones incluidas

- Inicio de sesión con Supabase Auth y autorización mediante el rol de `usuarios`.
- Administrador: alta, búsqueda, edición y baja lógica del personal.
- Gestor de capacitación: consulta de personal y registro de competencias; sin modificación de personal.
- Trabajador: consulta exclusiva de su expediente y de sus evaluaciones.
- Registro de evaluaciones, historial y selección transaccional del registro actual.
- Cálculo de vigencia a tres años, con soporte del 29 de febrero.
- Panel con estados Vigente, Por vencer, Vencida, Sin registro y No aprobado.
- Filtros por nombre/CUIP/CURP, corporación, situación y vigencia; paginación.
- Políticas RLS, catálogos separados y auditoría de cambios.

## Recorrer la demostración en Windows

Abre PowerShell en esta carpeta y ejecuta:

```powershell
.\Iniciar-Demo.ps1
```

El script instala las dependencias si faltan, inicia ambos servicios en segundo plano y muestra la dirección `http://127.0.0.1:5173`. Requiere Node.js 22 o posterior y Python 3.11 o posterior; si está disponible, puede usar el Python empaquetado de Codex. Las dependencias se descargan de npm y PyPI en el primer arranque.

Para detenerlos, usa `Detener-Demo.ps1`. La demostración guarda los cambios en memoria y los pierde al detener el backend. No se debe usar para información real. El modo demo se rechaza si `APP_ENV` no es `development` o si la aplicación se ejecuta en Vercel.

## Configurar el sistema real

Sigue [la guía de Supabase](docs/CONFIGURACION_SUPABASE.md). Contiene la migración, creación de usuarios, asignación de roles y variables de entorno. No se necesita una clave `service_role` para la aplicación: FastAPI consulta Supabase con el JWT del usuario, conservando las restricciones RLS.

## Estructura

```text
backend/
  app/core/          Configuración y autorización
  app/db/            Adaptadores Supabase y demostración
  app/services/      Reglas de vigencia
  app/schemas.py     Validación de entradas
  app/main.py        API REST
  tests/             Pruebas de API y negocio
frontend/
  src/               Interfaz React en español
supabase/
  migrations/        Modelo, funciones, permisos y auditoría
  tests/             Pruebas SQL y RLS con PostgreSQL local
docs/
  ANALISIS_ARQUITECTURA.md
  CONFIGURACION_SUPABASE.md
  VALIDACION.md
```

## Desarrollo y pruebas

Desde `backend`, con el entorno virtual activado:

```powershell
python -m pip install -r requirements-lock.txt
python -m pytest -q
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Desde `frontend`:

```powershell
npm ci
npm run dev
npm run build
npm run test:database
```

La documentación OpenAPI está en `http://127.0.0.1:8000/docs`. `requirements-lock.txt` y `package-lock.json` fijan las versiones verificadas. Las pruebas SQL usan PGlite para ejecutar PostgreSQL sin instalar un servidor; no reemplazan la validación final en un proyecto real de Supabase.

## Límite de esta entrega

Calendario, bitácora, importación masiva y documentos adjuntos corresponden a la fase 2. Notificaciones automáticas, cron, gráficas avanzadas y reportes exportables corresponden a la fase 3. El panel de fase 1 consulta la vigencia en tiempo real y no requiere cron.

Consulta [el análisis y las decisiones de implementación](docs/ANALISIS_ARQUITECTURA.md) y [los resultados de validación](docs/VALIDACION.md).
