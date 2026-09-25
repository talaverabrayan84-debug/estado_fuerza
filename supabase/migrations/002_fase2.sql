-- Ampliación no destructiva. Aplicar después de 001_fase1.sql.
begin;
create table public.cursos (
 id uuid primary key default gen_random_uuid(),
 nombre_curso varchar(200) not null check(length(trim(nombre_curso))>=3),
 tipo text not null check(tipo in ('formacion_inicial','competencias_basicas','actualizacion','especialidad')),
 fuente_financiamiento text not null check(fuente_financiamiento in ('FASP','FOFISP','recurso_propio','otro')),
 institucion_impartidora varchar(150) not null check(length(trim(institucion_impartidora))>=2),
 horas integer not null check(horas between 1 and 10000),
 vigencia_meses integer check(vigencia_meses between 1 and 120),
 created_at timestamptz not null default now(),
 check(tipo<>'competencias_basicas' or vigencia_meses is not distinct from 36)
);
create table public.curso_sesiones (
 id uuid primary key default gen_random_uuid(), curso_id uuid not null references public.cursos(id),
 fecha_inicio date not null, fecha_fin date not null,
 sede varchar(150) not null check(length(trim(sede))>=2),
 modalidad text not null check(modalidad in ('presencial','en_linea','mixta')),
 cupo integer not null check(cupo between 1 and 10000),
 created_at timestamptz not null default now(),
 check(fecha_fin>=fecha_inicio and fecha_fin-fecha_inicio<=1096)
);
create index sesiones_fechas_idx on public.curso_sesiones(fecha_inicio,fecha_fin);
create table public.inscripciones (
 id uuid primary key default gen_random_uuid(), personal_id uuid not null references public.personal(id),
 sesion_id uuid not null references public.curso_sesiones(id),
 fecha_inscripcion date not null default (now() at time zone 'America/Mexico_City')::date,
 estatus text not null default 'inscrito' check(estatus in ('inscrito','en_curso','concluido','baja')),
 calificacion numeric(5,2) check(calificacion between 0 and 100),
 unique(personal_id,sesion_id)
);
create index inscripciones_sesion_idx on public.inscripciones(sesion_id);
create table public.bitacora (
 id uuid primary key default gen_random_uuid(), personal_id uuid not null references public.personal(id),
 sesion_id uuid references public.curso_sesiones(id), fecha date not null,
 tipo_actividad text not null check(tipo_actividad in ('avance','incidencia','entrega','observacion')),
 descripcion text not null check(length(trim(descripcion)) between 3 and 5000),
 creado_por uuid not null references auth.users(id),
 created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create index bitacora_personal_fecha_idx on public.bitacora(personal_id,fecha desc);
create table public.carga_archivos (
 id uuid primary key default gen_random_uuid(), usuario_id uuid not null references auth.users(id),
 nombre_archivo varchar(200) not null, tipo_archivo text not null check(tipo_archivo in ('csv','xlsx')),
 tabla_destino text not null check(tabla_destino in ('personal','competencias_basicas')),
 estado text not null default 'revision' check(estado in ('revision','confirmada')),
 filas jsonb not null check(jsonb_typeof(filas)='array' and jsonb_array_length(filas) between 1 and 200),
 registros_procesados integer not null default 0, registros_error integer not null default 0,
 fecha_carga timestamptz not null default now(), expires_at timestamptz not null default now()+interval '1 hour',
 confirmado_at timestamptz
);
create index carga_usuario_fecha_idx on public.carga_archivos(usuario_id,fecha_carga desc);

do $$ declare t text; begin
 foreach t in array array['cursos','curso_sesiones','inscripciones','bitacora','carga_archivos'] loop
  execute format('alter table public.%I enable row level security',t);
  execute format('revoke all on public.%I from anon,authenticated',t);
  execute format('grant select on public.%I to authenticated',t);
 end loop;
end $$;
create policy cursos_lectura on public.cursos for select to authenticated using ((select private.rol_actual()) is not null);
create policy cursos_alta on public.cursos for insert to authenticated with check ((select private.rol_actual()) in ('admin','capacitacion'));
create policy cursos_edicion on public.cursos for update to authenticated using ((select private.rol_actual()) in ('admin','capacitacion')) with check ((select private.rol_actual()) in ('admin','capacitacion'));
create policy sesiones_lectura on public.curso_sesiones for select to authenticated using ((select private.rol_actual()) is not null);
create policy sesiones_alta on public.curso_sesiones for insert to authenticated with check ((select private.rol_actual()) in ('admin','capacitacion'));
create policy sesiones_edicion on public.curso_sesiones for update to authenticated using ((select private.rol_actual()) in ('admin','capacitacion')) with check ((select private.rol_actual()) in ('admin','capacitacion'));
create policy inscripciones_lectura on public.inscripciones for select to authenticated using ((select private.rol_actual()) in ('admin','capacitacion') or personal_id=(select private.personal_actual()));
create policy bitacora_lectura on public.bitacora for select to authenticated using ((select private.rol_actual()) in ('admin','capacitacion') or personal_id=(select private.personal_actual()));
create policy carga_admin on public.carga_archivos for select to authenticated using ((select private.rol_actual())='admin' and usuario_id=(select auth.uid()));
grant insert(nombre_curso,tipo,fuente_financiamiento,institucion_impartidora,horas,vigencia_meses),update(nombre_curso,tipo,fuente_financiamiento,institucion_impartidora,horas,vigencia_meses) on public.cursos to authenticated;
grant insert(curso_id,fecha_inicio,fecha_fin,sede,modalidad,cupo),update(curso_id,fecha_inicio,fecha_fin,sede,modalidad,cupo) on public.curso_sesiones to authenticated;

create function private.cupo_disponible() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if new.cupo < (select count(*) from public.inscripciones where sesion_id=new.id and estatus<>'baja') then
  raise exception 'El cupo es menor que las inscripciones activas' using errcode='P0001';
 end if;
 return new;
end $$;
create trigger validar_cupo before update on public.curso_sesiones for each row execute function private.cupo_disponible();
create function public.guardar_inscripcion(sesion uuid,datos jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare capacidad integer; persona uuid:=(datos->>'personal_id')::uuid; anterior public.inscripciones; registro public.inscripciones;
begin
 if coalesce(private.rol_actual(),'') not in ('admin','capacitacion') then raise exception 'Sin permiso' using errcode='42501'; end if;
 select cupo into capacidad from public.curso_sesiones where id=sesion for update;
 if not found then raise exception 'Sesión inexistente' using errcode='23503'; end if;
 select * into anterior from public.inscripciones where sesion_id=sesion and personal_id=persona;
 if (anterior.id is null or anterior.estatus='baja') and datos->>'estatus'<>'baja' then
  if (select count(*) from public.inscripciones where sesion_id=sesion and estatus<>'baja')>=capacidad then
   raise exception 'No hay cupo disponible' using errcode='P0001';
  end if;
 end if;
 insert into public.inscripciones(sesion_id,personal_id,estatus,calificacion)
 values(sesion,persona,datos->>'estatus',(datos->>'calificacion')::numeric)
 on conflict(personal_id,sesion_id) do update set estatus=excluded.estatus,calificacion=excluded.calificacion
 returning * into registro;
 return to_jsonb(registro);
end $$;

create view public.vw_curso_sesiones with(security_invoker=true) as
 select s.*,c.nombre_curso,c.tipo,c.fuente_financiamiento,c.institucion_impartidora,c.horas,
 case when (now() at time zone 'America/Mexico_City')::date<s.fecha_inicio then 'Próximo'
 when (now() at time zone 'America/Mexico_City')::date>s.fecha_fin then 'Concluido' else 'En curso' end as estatus,
 -- El trabajador solo ve su propia inscripción; no se expone el padrón ajeno.
 (select count(*) from public.inscripciones i where i.sesion_id=s.id and i.estatus<>'baja') as inscripciones_visibles
 from public.curso_sesiones s join public.cursos c on c.id=s.curso_id;
grant select on public.vw_curso_sesiones to authenticated;
revoke all on public.vw_curso_sesiones from anon;

create function public.guardar_bitacora(datos jsonb,entrada uuid default null) returns jsonb language plpgsql security definer set search_path='' as $$
declare persona uuid:=private.personal_actual(); sesion uuid:=(datos->>'sesion_id')::uuid; registro public.bitacora; v_fecha date:=(datos->>'fecha')::date;
begin
 if private.rol_actual() is distinct from 'trabajador' or persona is null then raise exception 'Sin permiso' using errcode='42501'; end if;
 if v_fecha>(now() at time zone 'America/Mexico_City')::date then raise exception 'Fecha futura' using errcode='22023'; end if;
 if sesion is not null and not exists(select 1 from public.inscripciones where personal_id=persona and sesion_id=sesion and estatus<>'baja') then
  raise exception 'Se requiere inscripción en la sesión' using errcode='42501';
 end if;
 if entrada is null then
  insert into public.bitacora(personal_id,sesion_id,fecha,tipo_actividad,descripcion,creado_por)
  values(persona,sesion,v_fecha,datos->>'tipo_actividad',trim(datos->>'descripcion'),auth.uid()) returning * into registro;
 else
  update public.bitacora set sesion_id=sesion,fecha=v_fecha,tipo_actividad=datos->>'tipo_actividad',descripcion=trim(datos->>'descripcion'),updated_at=now()
  where id=entrada and personal_id=persona and creado_por=auth.uid() returning * into registro;
  if not found then raise exception 'Entrada no disponible' using errcode='42501'; end if;
 end if;
 return to_jsonb(registro);
end $$;

create function public.preparar_carga(datos jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare registro public.carga_archivos;
begin
 if private.rol_actual() is distinct from 'admin' then raise exception 'Sin permiso' using errcode='42501'; end if;
 insert into public.carga_archivos(usuario_id,nombre_archivo,tipo_archivo,tabla_destino,filas,registros_error)
 values(auth.uid(),datos->>'nombre_archivo',datos->>'tipo_archivo',datos->>'tabla_destino',datos->'filas',
 (select count(*) from jsonb_array_elements(datos->'filas') f where jsonb_array_length(f->'errores')>0)) returning * into registro;
 return to_jsonb(registro);
end $$;

create function public.confirmar_carga(carga uuid) returns jsonb language plpgsql security definer set search_path='' as $$
declare lote public.carga_archivos; fila jsonb; d jsonb; p public.personal; objetivo uuid; contador integer:=0;
begin
 if private.rol_actual() is distinct from 'admin' then raise exception 'Sin permiso' using errcode='42501'; end if;
 select * into lote from public.carga_archivos where id=carga and usuario_id=auth.uid() for update;
 if not found then raise exception 'Carga no disponible' using errcode='42501'; end if;
 if lote.estado='confirmada' then return to_jsonb(lote); end if;
 if lote.expires_at<=now() then raise exception 'La revisión ha caducado. Vuelva a cargar el archivo.' using errcode='P0001'; end if;
 if lote.registros_error>0 then raise exception 'Corrija todas las filas antes de confirmar' using errcode='22023'; end if;
 for fila in select value from jsonb_array_elements(lote.filas) loop
  d:=fila->'datos'; objetivo:=(fila->>'personal_id')::uuid;
  if lote.tabla_destino='personal' then
   if objetivo is not null then
    select * into p from public.personal where id=objetivo for update;
    if not found or p.updated_at is distinct from (fila->>'version')::timestamptz then
     raise exception 'Un expediente cambió desde la revisión. Vuelva a cargar el archivo.' using errcode='P0001';
    end if;
    update public.personal set cuip=d->>'cuip',curp=d->>'curp',nombre_completo=d->>'nombre_completo',sexo=d->>'sexo',
    corporacion_id=(d->>'corporacion_id')::uuid,adscripcion=d->>'adscripcion',cargo_id=(d->>'cargo_id')::uuid,
    grado_id=(d->>'grado_id')::uuid,estatus=d->>'estatus' where id=objetivo;
   else
    insert into public.personal(cuip,curp,nombre_completo,sexo,corporacion_id,adscripcion,cargo_id,grado_id,estatus)
    values(d->>'cuip',d->>'curp',d->>'nombre_completo',d->>'sexo',(d->>'corporacion_id')::uuid,d->>'adscripcion',
    (d->>'cargo_id')::uuid,(d->>'grado_id')::uuid,d->>'estatus');
   end if;
  else
   perform public.registrar_competencia(d);
  end if;
  contador:=contador+1;
 end loop;
 update public.carga_archivos set estado='confirmada',registros_procesados=contador,confirmado_at=now() where id=carga returning * into lote;
 return to_jsonb(lote);
end $$;

do $$ declare t text; begin
 foreach t in array array['cursos','curso_sesiones','inscripciones','bitacora'] loop
  execute format('create trigger auditar_%I after insert or update on public.%I for each row execute function private.auditar()',t,t);
 end loop;
end $$;
revoke all on function private.cupo_disponible() from public;
revoke all on function public.guardar_inscripcion(uuid,jsonb),public.guardar_bitacora(jsonb,uuid),public.preparar_carga(jsonb),public.confirmar_carga(uuid) from public,anon;
grant execute on function public.guardar_inscripcion(uuid,jsonb),public.guardar_bitacora(jsonb,uuid),public.preparar_carga(jsonb),public.confirmar_carga(uuid) to authenticated;
commit;
