# Sistema de Gestión del Estado de Fuerza

Implementación de las fases 1 y 2 definidas en `Arquitectura_Sistema_Estado_de_Fuerza.docx`, versión 1.0. Incluye React 18 + TypeScript + Tailwind, FastAPI y migraciones PostgreSQL para Supabase.

La demostración local permite recorrer los tres perfiles con datos ficticios. El sistema está publicado en [Vercel](https://estado-fuerza-web-staging.vercel.app), conectado al proyecto Supabase `estado-fuerza-2026`. Se instalaron las cuatro migraciones y las bitácoras del Excel de referencia; el ingreso con la cuenta administradora de pruebas y la lectura de ambas hojas se verificaron desde la URL pública. Consulta [el estado del entorno](docs/STAGING.md) y [la revisión de pruebas y correcciones](docs/VALIDACION_QA.md).

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
- Calendario mensual y agenda, catálogo de cursos y programación de sesiones.
- Inscripciones, control de cupo, estados de participación y calificaciones.
- Bitácora del trabajador, con captura y edición de actividades propias.
- Evidencia privada por actividad: PDF, PNG o JPG, hasta 2 MB.
- Importación CSV/XLSX de personal y competencias básicas: plantillas, revisión por fila, confirmación transaccional y reporte de resultados.
- Bitácoras institucionales FASP y FOFISP con la estructura, celdas combinadas y formato del Excel de referencia; edición con control de versión.
- Alertas de entregas UMS dentro del sistema a 7, 3 y 1 días, el día de entrega y después del vencimiento; cierre por recepción completa.

Consulta [el alcance y recorrido de la fase 2](docs/FASE2.md).

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
  app/services/      Vigencia, calendario y validación de importaciones
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
npm test
npm run test:database
```

La documentación OpenAPI está en `http://127.0.0.1:8000/docs`. `requirements-lock.txt` y `package-lock.json` fijan las versiones verificadas. Las pruebas SQL usan PGlite para ejecutar PostgreSQL sin instalar un servidor; no reemplazan la validación final en un proyecto real de Supabase.

## Límite de esta entrega

La fase 2 incluye calendario, bitácora, evidencias e importación de las dos entidades ya implementadas: personal y competencias básicas. El registro especializado de formación inicial y otras certificaciones aún requiere su módulo propio; clasificar un curso como formación inicial no crea ese expediente de certificación.

Las alertas UMS se consultan dentro del sistema y se actualizan cada minuto. Envíos por correo o SMS, cron, gráficas y reportes generales corresponden a la fase 3. El reporte CSV de una importación forma parte de la fase 2. La vigencia y el estado de las sesiones se calculan al consultar.

Consulta [el análisis y las decisiones de implementación](docs/ANALISIS_ARQUITECTURA.md) y [los resultados de validación](docs/VALIDACION.md).
