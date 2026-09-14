# Validación de la fase 1

La API y las reglas de negocio superaron 20 pruebas automatizadas. La migración se ejecutó en PostgreSQL local mediante PGlite y superó 28 verificaciones de SQL y permisos RLS. La interfaz pasó la compilación TypeScript y la compilación de producción de Vite.

## Casos comprobados

- Vencimiento ayer, hoy, a 90 días y a 91 días; umbral configurable.
- Certificación del 29 de febrero y coincidencia de resultado entre Python y PostgreSQL.
- Alta, normalización de identificadores, rechazo de duplicados y baja lógica.
- CUIP/CURP obligatorios de manera alternativa y rechazo de estructura CURP inválida.
- Validación de catálogo, campos inesperados y fechas futuras.
- Administrador con acceso de captura y consulta; capacitación sin edición de personal.
- Trabajador limitado a su expediente y evaluaciones, incluso mediante consulta directa a la vista SQL.
- Rechazo de modificación de roles desde un cliente autenticado.
- Rechazo de escritura directa de evaluaciones; uso obligatorio de la función transaccional.
- Evaluación histórica sin reemplazo del registro actual; una sola evaluación activa.
- Rechazo de duplicado con reversión transaccional de la desactivación previa.
- Resultado no aprobado sin vigencia acreditada.
- Denegación de acceso anónimo e inhabilitación de cuentas.
- Auditoría de cambios y restricción de su lectura.
- Búsqueda, paginación, resumen y cierre de la sesión de demostración.
- Propagación del JWT del usuario al adaptador Supabase.

## Alcance de las pruebas

Las pruebas de API ejecutan el modo de demostración y un transporte simulado para el adaptador Supabase. Las pruebas de base usan PostgreSQL mediante PGlite con `auth.users` y `auth.uid()` simulados. No hay un proyecto real de Supabase configurado, por lo que aún no se ha verificado el flujo Auth → FastAPI → PostgREST contra el servicio alojado.

La restricción de un registro activo y la operación transaccional se verificaron en PostgreSQL local. Una prueba de concurrencia con varias conexiones reales debe realizarse al conectar Supabase. No se ejecutaron pruebas de carga ni una auditoría integral de seguridad o accesibilidad. La interfaz fue compilada; no se realizó una prueba automatizada de interacción en navegador.

## Criterio de aceptación al conectar Supabase

1. Crear cuentas para los tres roles y aplicar catálogos reales.
2. Dar de alta un expediente y comprobar que permanece después de reiniciar los servicios.
3. Registrar una evaluación aprobada y confirmar fecha de vencimiento y alertas.
4. Registrar una renovación y comprobar que se conserva el histórico.
5. Verificar con dos trabajadores distintos que ninguno puede consultar al otro.
6. Deshabilitar una cuenta y confirmar que pierde acceso a los datos.
7. Confirmar con DGSDP la regla ante un nuevo resultado no aprobado, la longitud oficial de CUIP y los catálogos.

## Reproducir

Desde `backend`: `python -m pytest -q`.

Desde `frontend`: `npm run test:database` y `npm run build`.
