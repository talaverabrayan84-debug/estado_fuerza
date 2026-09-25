-- Ejecutar como administrador en SQL Editor después de las tres migraciones.
-- Solo lectura. Cada fila debe devolver correcto=true antes de habilitar pruebas.
-- No devuelve expedientes, correos, tokens ni credenciales.
-- Complementar con login, carga y descarga HTTP reales: SQL no prueba esos servicios.
begin transaction read only;
with tablas(nombre) as (
 values ('corporaciones'),('cargos'),('grados'),('personal'),('usuarios'),
 ('configuracion'),('competencias_basicas'),('auditoria'),('cursos'),
 ('curso_sesiones'),('inscripciones'),('bitacora'),('carga_archivos'),('bitacora_evidencias')
), funciones(firma) as (
 values ('public.registrar_competencia(jsonb)'),('public.resumen_vigencia()'),
 ('public.guardar_inscripcion(uuid,jsonb)'),('public.guardar_bitacora(jsonb,uuid)'),
 ('public.preparar_carga(jsonb)'),('public.confirmar_carga(uuid)'),('public.vincular_evidencia(uuid,jsonb)')
), vistas(nombre) as (
 values ('vw_vigencia_competencias'),('vw_curso_sesiones')
), comprobaciones as (
 select 'tabla y RLS: '||t.nombre as comprobacion,
 coalesce(c.relkind='r' and c.relrowsecurity,false) as correcto
 from tablas t left join pg_class c on c.oid=to_regclass('public.'||t.nombre)
 union all
 select 'sin SELECT anónimo: '||t.nombre,
 not coalesce(has_table_privilege('anon',to_regclass('public.'||t.nombre),'SELECT'),true) from tablas t
 union all
 select 'vista invoca RLS: '||v.nombre,
 coalesce(c.reloptions @> array['security_invoker=true'],false)
 from vistas v left join pg_class c on c.oid=to_regclass('public.'||v.nombre)
 union all
 select 'RPC autenticada y no anónima: '||f.firma,
 coalesce(has_function_privilege('authenticated',to_regprocedure(f.firma),'EXECUTE')
 and not has_function_privilege('anon',to_regprocedure(f.firma),'EXECUTE'),false) from funciones f
 union all
 select 'funciones SECURITY DEFINER con search_path fijo',
 not exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname in ('public','private') and p.prosecdef
 and p.proname in ('rol_actual','personal_actual','auditar','registrar_competencia','cupo_disponible',
 'guardar_inscripcion','guardar_bitacora','preparar_carga','confirmar_carga','evidencia_permitida','vincular_evidencia')
 and not coalesce(p.proconfig @> array['search_path=""'],false))
 union all
 select 'usuarios sin escritura autenticada',not (
 has_any_column_privilege('authenticated','public.usuarios','INSERT') or
 has_any_column_privilege('authenticated','public.usuarios','UPDATE') or
 has_table_privilege('authenticated','public.usuarios','DELETE'))
 union all
 select 'bucket privado con límites',exists(select 1 from storage.buckets
 where id='bitacora-evidencias' and not public and file_size_limit=2097152
 and allowed_mime_types @> array['application/pdf','image/png','image/jpeg']
 and cardinality(allowed_mime_types)=3)
 union all
 select 'RLS de Storage activa',coalesce((select relrowsecurity from pg_class where oid=to_regclass('storage.objects')),false)
 union all
 select 'tres políticas de evidencia presentes',count(*)=3 from pg_policies
 where schemaname='storage' and tablename='objects'
 and policyname in ('evidencia_subir','evidencia_descargar','evidencia_limpieza')
 union all
 select 'configuración inicial presente',exists(select 1 from public.configuracion where id=1 and dias_alerta between 0 and 365)
)
select comprobacion,correcto from comprobaciones order by comprobacion;
commit;
