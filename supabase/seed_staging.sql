-- OPCIONAL: ejecutar solo en el proyecto de pruebas, después de 001, 002 y 003.
-- Datos exclusivamente sintéticos. No crea cuentas Auth, contraseñas ni permisos.
-- Repetir el archivo no duplica registros ni sobrescribe cambios hechos en pruebas.
-- Las fechas se calculan en la primera ejecución; las posteriores las conservan.
begin;

insert into public.corporaciones(id,nombre) values
 ('90000000-0000-4000-8000-000000000001','PRUEBAS - Corporación ficticia')
on conflict do nothing;
insert into public.cargos(id,nombre) values
 ('90000000-0000-4000-8000-000000000002','PRUEBAS - Cargo ficticio')
on conflict do nothing;
insert into public.grados(id,nombre) values
 ('90000000-0000-4000-8000-000000000003','PRUEBAS - Grado ficticio')
on conflict do nothing;

insert into public.personal(id,cuip,nombre_completo,sexo,corporacion_id,adscripcion,cargo_id,grado_id)
select v.id::uuid,v.cuip,v.nombre,null,
 '90000000-0000-4000-8000-000000000001'::uuid,'PRUEBAS - Unidad ficticia',
 '90000000-0000-4000-8000-000000000002'::uuid,'90000000-0000-4000-8000-000000000003'::uuid
from (values
 ('91000000-0000-4000-8000-000000000001','SIMULADO001','PRUEBAS - Persona ficticia 001'),
 ('91000000-0000-4000-8000-000000000002','SIMULADO002','PRUEBAS - Persona ficticia 002'),
 ('91000000-0000-4000-8000-000000000003','SIMULADO003','PRUEBAS - Persona ficticia 003'),
 ('91000000-0000-4000-8000-000000000004','SIMULADO004','PRUEBAS - Persona ficticia 004'),
 ('91000000-0000-4000-8000-000000000005','SIMULADO005','PRUEBAS - Persona ficticia 005')
) v(id,cuip,nombre)
on conflict do nothing;

-- El trigger calcula los vencimientos; se cubren los cinco estados del panel.
-- Se omite creado_por porque este archivo no suplanta una cuenta de Auth.
insert into public.competencias_basicas(id,personal_id,institucion_evaluadora,fecha_certificacion,resultado,folio)
select v.id::uuid,v.persona::uuid,'PRUEBAS - Academia ficticia',
 ((now() at time zone 'America/Mexico_City')::date-v.antiguedad)::date,v.resultado,v.folio
from (values
 ('92000000-0000-4000-8000-000000000001','91000000-0000-4000-8000-000000000001',interval '1 year','aprobado','PRUEBAS-VIGENTE'),
 ('92000000-0000-4000-8000-000000000002','91000000-0000-4000-8000-000000000002',interval '3 years' - interval '30 days','aprobado','PRUEBAS-PORVENCER'),
 ('92000000-0000-4000-8000-000000000003','91000000-0000-4000-8000-000000000003',interval '4 years','aprobado','PRUEBAS-VENCIDA'),
 ('92000000-0000-4000-8000-000000000004','91000000-0000-4000-8000-000000000004',interval '1 day','no_aprobado','PRUEBAS-NOAPROBADO')
) v(id,persona,antiguedad,resultado,folio)
on conflict do nothing;

insert into public.cursos(id,nombre_curso,tipo,fuente_financiamiento,institucion_impartidora,horas,vigencia_meses) values
 ('93000000-0000-4000-8000-000000000001','PRUEBAS - Actualización ficticia','actualizacion','recurso_propio','PRUEBAS - Academia ficticia',20,null),
 ('93000000-0000-4000-8000-000000000002','PRUEBAS - Competencias ficticias','competencias_basicas','FASP','PRUEBAS - Academia ficticia',40,36)
on conflict do nothing;
insert into public.curso_sesiones(id,curso_id,fecha_inicio,fecha_fin,sede,modalidad,cupo)
select v.id::uuid,v.curso::uuid,(now() at time zone 'America/Mexico_City')::date+v.inicio,
 (now() at time zone 'America/Mexico_City')::date+v.fin,'PRUEBAS - Aula ficticia','presencial',10
from (values
 ('94000000-0000-4000-8000-000000000001','93000000-0000-4000-8000-000000000001',-1,1),
 ('94000000-0000-4000-8000-000000000002','93000000-0000-4000-8000-000000000002',7,8),
 ('94000000-0000-4000-8000-000000000003','93000000-0000-4000-8000-000000000001',-10,-9)
) v(id,curso,inicio,fin)
on conflict do nothing;
insert into public.inscripciones(id,personal_id,sesion_id,estatus) values
 ('95000000-0000-4000-8000-000000000001','91000000-0000-4000-8000-000000000001','94000000-0000-4000-8000-000000000001','en_curso'),
 ('95000000-0000-4000-8000-000000000002','91000000-0000-4000-8000-000000000002','94000000-0000-4000-8000-000000000001','inscrito')
on conflict do nothing;

-- Para bitácora/evidencia: crear una cuenta real de pruebas con la interfaz Auth,
-- vincularla manualmente a uno de estos expedientes como trabajador e iniciar sesión.
-- Este seed nunca modifica public.usuarios ni crea objetos de Storage.
commit;
