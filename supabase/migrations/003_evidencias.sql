-- Supabase Storage ya debe estar habilitado. Aplicar después de 002_fase2.sql.
begin;
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values('bitacora-evidencias','bitacora-evidencias',false,2097152,array['application/pdf','image/png','image/jpeg']);
create table public.bitacora_evidencias (
 id uuid primary key default gen_random_uuid(),
 bitacora_id uuid not null unique references public.bitacora(id),
 ruta text not null unique, nombre varchar(200) not null,
 tipo text not null check(tipo in ('application/pdf','image/png','image/jpeg')),
 tamano integer not null check(tamano between 1 and 2097152),
 created_at timestamptz not null default now()
);
alter table public.bitacora_evidencias enable row level security;
revoke all on public.bitacora_evidencias from anon,authenticated;
grant select on public.bitacora_evidencias to authenticated;
create policy evidencia_lectura on public.bitacora_evidencias for select to authenticated
using(exists(select 1 from public.bitacora b where b.id=bitacora_id));

create function private.evidencia_permitida(ruta text,escritura boolean) returns boolean
language plpgsql stable security definer set search_path='' as $$
declare partes text[]:=string_to_array(ruta,'/'); entrada public.bitacora; rol text:=private.rol_actual();
begin
 if array_length(partes,1)<>3 or partes[1]!~'^[0-9a-f-]{36}$' or partes[2]!~'^[0-9a-f-]{36}$'
 or partes[3]!~'^[0-9a-f-]{36}\.(pdf|png|jpg)$' then return false; end if;
 select * into entrada from public.bitacora where id::text=partes[2] and personal_id::text=partes[1];
 if not found then return false; end if;
 if escritura then
  return rol='trabajador' and entrada.personal_id=private.personal_actual() and entrada.creado_por=auth.uid();
 end if;
 return rol in ('admin','capacitacion') or (rol='trabajador' and entrada.personal_id=private.personal_actual());
end $$;
revoke all on function private.evidencia_permitida(text,boolean) from public;
grant execute on function private.evidencia_permitida(text,boolean) to authenticated;
create policy evidencia_subir on storage.objects for insert to authenticated
with check(bucket_id='bitacora-evidencias' and private.evidencia_permitida(name,true)
 and not exists(select 1 from public.bitacora_evidencias e where e.bitacora_id::text=split_part(name,'/',2)));
create policy evidencia_descargar on storage.objects for select to authenticated
using(bucket_id='bitacora-evidencias' and private.evidencia_permitida(name,false));
-- Solo se eliminan objetos sin vincular, para recuperar cargas fallidas.
create policy evidencia_limpieza on storage.objects for delete to authenticated
using(bucket_id='bitacora-evidencias' and private.evidencia_permitida(name,true)
 and not exists(select 1 from public.bitacora_evidencias e where e.ruta=name));

create function public.vincular_evidencia(entrada uuid,datos jsonb) returns jsonb
language plpgsql security definer set search_path='' as $$
declare registro public.bitacora_evidencias; ruta text:=datos->>'ruta';
begin
 if not coalesce(private.evidencia_permitida(ruta,true),false) or split_part(ruta,'/',2)<>entrada::text then
  raise exception 'Sin permiso' using errcode='42501';
 end if;
 perform 1 from public.bitacora where id=entrada for update;
 if not exists(select 1 from storage.objects o where o.bucket_id='bitacora-evidencias' and o.name=ruta) then
  raise exception 'Archivo no disponible' using errcode='23503';
 end if;
 insert into public.bitacora_evidencias(bitacora_id,ruta,nombre,tipo,tamano)
 values(entrada,ruta,datos->>'nombre',datos->>'tipo',(datos->>'tamano')::integer) returning * into registro;
 return to_jsonb(registro);
end $$;
revoke all on function public.vincular_evidencia(uuid,jsonb) from public,anon;
grant execute on function public.vincular_evidencia(uuid,jsonb) to authenticated;
create trigger auditar_evidencia after insert on public.bitacora_evidencias for each row execute function private.auditar();
commit;
