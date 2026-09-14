-- Ejecutar una vez en un proyecto Supabase vacío (PostgreSQL 15+).
begin;
create schema if not exists private;
revoke all on schema private from public;
grant usage on schema private to authenticated;

create table public.corporaciones (
 id uuid primary key default gen_random_uuid(), nombre varchar(100) not null unique,
 activo boolean not null default true, check (length(trim(nombre)) > 0)
);
create table public.cargos (
 id uuid primary key default gen_random_uuid(), nombre varchar(100) not null unique,
 activo boolean not null default true, check (length(trim(nombre)) > 0)
);
create table public.grados (
 id uuid primary key default gen_random_uuid(), nombre varchar(100) not null unique,
 activo boolean not null default true, check (length(trim(nombre)) > 0)
);
create table public.personal (
 id uuid primary key default gen_random_uuid(),
 cuip varchar(20) unique, curp varchar(18) unique,
 nombre_completo varchar(150) not null check (length(trim(nombre_completo)) >= 3),
 sexo varchar(1) check (sexo in ('H','M')),
 corporacion_id uuid not null references public.corporaciones(id),
 adscripcion varchar(150) not null check (length(trim(adscripcion)) > 0),
 cargo_id uuid references public.cargos(id), grado_id uuid references public.grados(id),
 estatus varchar(20) not null default 'activo' check (estatus in ('activo','baja','comisionado','licencia')),
 created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
 constraint identificador_requerido check (cuip is not null or curp is not null),
 constraint cuip_formato check (cuip ~ '^[A-Z0-9]{1,20}$'),
 constraint curp_formato check (curp ~ '^[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[A-Z0-9][0-9]$')
);
create index personal_corporacion_estatus_idx on public.personal(corporacion_id, estatus);
create index personal_nombre_idx on public.personal(nombre_completo);
create table public.usuarios (
 id uuid primary key references auth.users(id) on delete cascade,
 personal_id uuid unique references public.personal(id),
 rol varchar(20) not null check (rol in ('admin','capacitacion','trabajador')),
 activo boolean not null default true,
 check (rol <> 'trabajador' or personal_id is not null)
);
create table public.configuracion (
 id smallint primary key default 1 check (id = 1),
 dias_alerta integer not null default 90 check (dias_alerta between 0 and 365)
);
insert into public.configuracion(id) values (1);
create table public.competencias_basicas (
 id uuid primary key default gen_random_uuid(),
 personal_id uuid not null references public.personal(id),
 institucion_evaluadora varchar(150) not null check (length(trim(institucion_evaluadora)) >= 2),
 fecha_certificacion date not null,
 fecha_vencimiento date,
 resultado varchar(20) not null check (resultado in ('aprobado','no_aprobado')),
 folio varchar(60) not null check (length(trim(folio)) > 0),
 activo boolean not null default true,
 creado_por uuid references auth.users(id),
 created_at timestamptz not null default now(),
 unique (personal_id, fecha_certificacion, folio)
);
create unique index competencias_un_activo_idx on public.competencias_basicas(personal_id) where activo;
create index competencias_historial_idx on public.competencias_basicas(personal_id, fecha_certificacion desc);
create table public.auditoria (
 id bigint generated always as identity primary key,
 usuario_id uuid, tabla text not null, registro_id uuid not null, operacion text not null,
 datos_anteriores jsonb, datos_nuevos jsonb, created_at timestamptz not null default now()
);

create function private.rol_actual() returns text language sql stable security definer
set search_path = '' as $$
 select rol from public.usuarios where id = (select auth.uid()) and activo
$$;
create function private.personal_actual() returns uuid language sql stable security definer
set search_path = '' as $$
 select personal_id from public.usuarios where id = (select auth.uid()) and activo
$$;
revoke all on function private.rol_actual(), private.personal_actual() from public;
grant execute on function private.rol_actual(), private.personal_actual() to authenticated;

alter table public.personal enable row level security;
alter table public.usuarios enable row level security;
alter table public.competencias_basicas enable row level security;
alter table public.corporaciones enable row level security;
alter table public.cargos enable row level security;
alter table public.grados enable row level security;
alter table public.configuracion enable row level security;
alter table public.auditoria enable row level security;

create policy personal_lectura on public.personal for select to authenticated using (
 (select private.rol_actual()) in ('admin','capacitacion') or id = (select private.personal_actual())
);
create policy personal_alta on public.personal for insert to authenticated with check ((select private.rol_actual()) = 'admin');
create policy personal_edicion on public.personal for update to authenticated
 using ((select private.rol_actual()) = 'admin') with check ((select private.rol_actual()) = 'admin');
create policy usuario_propio on public.usuarios for select to authenticated using (id = (select auth.uid()));
create policy competencias_lectura on public.competencias_basicas for select to authenticated using (
 (select private.rol_actual()) in ('admin','capacitacion') or personal_id = (select private.personal_actual())
);
create policy corporaciones_lectura on public.corporaciones for select to authenticated using ((select private.rol_actual()) is not null);
create policy cargos_lectura on public.cargos for select to authenticated using ((select private.rol_actual()) is not null);
create policy grados_lectura on public.grados for select to authenticated using ((select private.rol_actual()) is not null);
create policy configuracion_lectura on public.configuracion for select to authenticated using ((select private.rol_actual()) is not null);
create policy auditoria_admin on public.auditoria for select to authenticated using ((select private.rol_actual()) = 'admin');

-- Sin permisos de escritura a usuarios ni a competencias: las altas de evaluación
-- pasan exclusivamente por la función transaccional, también desde PostgREST.
revoke all on public.personal, public.usuarios, public.competencias_basicas,
 public.corporaciones, public.cargos, public.grados, public.configuracion, public.auditoria from anon, authenticated;
grant select on public.personal, public.usuarios, public.competencias_basicas,
 public.corporaciones, public.cargos, public.grados, public.configuracion, public.auditoria to authenticated;
grant insert(cuip,curp,nombre_completo,sexo,corporacion_id,adscripcion,cargo_id,grado_id,estatus),
 update(cuip,curp,nombre_completo,sexo,corporacion_id,adscripcion,cargo_id,grado_id,estatus) on public.personal to authenticated;

create function private.preparar_personal() returns trigger language plpgsql set search_path = '' as $$
begin
 new.cuip := nullif(upper(trim(new.cuip)), '');
 new.curp := nullif(upper(trim(new.curp)), '');
 new.nombre_completo := trim(new.nombre_completo);
 new.adscripcion := trim(new.adscripcion);
 new.updated_at := now();
 return new;
end $$;
create trigger preparar_personal before insert or update on public.personal
 for each row execute function private.preparar_personal();

create function private.calcular_vencimiento() returns trigger language plpgsql set search_path = '' as $$
begin
 if new.fecha_certificacion > (now() at time zone 'America/Mexico_City')::date then
  raise exception 'Fecha futura' using errcode = '22023';
 end if;
 new.fecha_vencimiento := case when new.resultado = 'aprobado'
  then (new.fecha_certificacion + interval '3 years')::date else null end;
 return new;
end $$;
create trigger calcular_vencimiento before insert or update on public.competencias_basicas
 for each row execute function private.calcular_vencimiento();

create function private.auditar() returns trigger language plpgsql security definer set search_path = '' as $$
begin
 insert into public.auditoria(usuario_id,tabla,registro_id,operacion,datos_anteriores,datos_nuevos)
 values(auth.uid(),tg_table_name,new.id,tg_op,
 case when tg_op = 'UPDATE' then to_jsonb(old) else null end,to_jsonb(new));
 return new;
end $$;
create trigger auditar_personal after insert or update on public.personal for each row execute function private.auditar();
create trigger auditar_competencias after insert or update on public.competencias_basicas for each row execute function private.auditar();

create function public.registrar_competencia(datos jsonb) returns jsonb language plpgsql security definer
set search_path = '' as $$
declare
 persona uuid := (datos->>'personal_id')::uuid;
 fecha date := (datos->>'fecha_certificacion')::date;
 fecha_actual date;
 es_actual boolean;
 registro public.competencias_basicas;
begin
 if coalesce(private.rol_actual(),'') not in ('admin','capacitacion') then
  raise exception 'Sin permiso' using errcode = '42501';
 end if;
 -- Serializa renovaciones de la misma persona y mantiene histórico íntegro.
 perform 1 from public.personal where id = persona for update;
 if not found then raise exception 'Personal inexistente' using errcode = '23503'; end if;
 select fecha_certificacion into fecha_actual from public.competencias_basicas where personal_id = persona and activo;
 es_actual := fecha_actual is null or fecha >= fecha_actual;
 if es_actual then update public.competencias_basicas set activo = false where personal_id = persona and activo; end if;
 insert into public.competencias_basicas(personal_id,institucion_evaluadora,fecha_certificacion,resultado,folio,activo,creado_por)
 values(persona,trim(datos->>'institucion_evaluadora'),fecha,datos->>'resultado',trim(datos->>'folio'),es_actual,auth.uid())
 returning * into registro;
 return to_jsonb(registro);
end $$;
revoke all on function public.registrar_competencia(jsonb) from public, anon;
grant execute on function public.registrar_competencia(jsonb) to authenticated;

create view public.vw_vigencia_competencias with (security_invoker = true) as
select p.id as personal_id, p.cuip, p.curp, p.nombre_completo, p.sexo,
 p.corporacion_id, c.nombre as corporacion, p.adscripcion, p.cargo_id, ca.nombre as cargo,
 p.grado_id, g.nombre as grado, p.estatus, p.created_at, p.updated_at,
 cb.id as competencia_id, cb.fecha_certificacion, cb.fecha_vencimiento, cb.resultado,
 cb.institucion_evaluadora, cb.folio,
 case when cb.id is null then 'Sin registro'
 when cb.resultado = 'no_aprobado' then 'No aprobado'
 when cb.fecha_vencimiento < (now() at time zone 'America/Mexico_City')::date then 'Vencida'
 when cb.fecha_vencimiento <= (now() at time zone 'America/Mexico_City')::date + cfg.dias_alerta then 'Por vencer'
 else 'Vigente' end as estatus_vigencia,
 cb.fecha_vencimiento - (now() at time zone 'America/Mexico_City')::date as dias_restantes
from public.personal p
join public.corporaciones c on c.id = p.corporacion_id
left join public.cargos ca on ca.id = p.cargo_id
left join public.grados g on g.id = p.grado_id
left join public.competencias_basicas cb on cb.personal_id = p.id and cb.activo
cross join public.configuracion cfg;
revoke all on public.vw_vigencia_competencias from anon;
grant select on public.vw_vigencia_competencias to authenticated;

create function public.resumen_vigencia() returns jsonb language sql stable security invoker set search_path = '' as $$
 select jsonb_build_object('total',count(*),'Vigente',count(*) filter(where estatus_vigencia='Vigente'),
 'Por vencer',count(*) filter(where estatus_vigencia='Por vencer'),'Vencida',count(*) filter(where estatus_vigencia='Vencida'),
 'Sin registro',count(*) filter(where estatus_vigencia='Sin registro'),'No aprobado',count(*) filter(where estatus_vigencia='No aprobado'))
 from public.vw_vigencia_competencias where estatus = 'activo'
$$;
revoke all on function public.resumen_vigencia() from public, anon;
grant execute on function public.resumen_vigencia() to authenticated;
-- Las funciones trigger no son una API pública.
revoke all on function private.preparar_personal(), private.calcular_vencimiento(), private.auditar() from public;
commit;
