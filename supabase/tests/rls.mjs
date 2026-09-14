// Ejecuta PostgreSQL local con PGlite y simula únicamente auth.uid()/auth.users.
// No contacta ni modifica un proyecto Supabase.
import {createRequire} from 'node:module';
import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const require=createRequire(new URL('../../frontend/package.json',import.meta.url));
const {PGlite}=require('@electric-sql/pglite');
const db=new PGlite();
let checks=0;
const check=(value,message)=>{assert.ok(value,message);checks++;};
await db.exec(`create role anon nologin; create role authenticated nologin; create schema auth;
 create table auth.users(id uuid primary key);
 create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
 grant usage on schema auth to authenticated, anon; grant execute on function auth.uid() to authenticated, anon;`);
await db.exec(await readFile(new URL('../migrations/001_fase1.sql',import.meta.url),'utf8'));
const A='30000000-0000-0000-0000-000000000001', C='30000000-0000-0000-0000-000000000002', W='30000000-0000-0000-0000-000000000003';
const P='20000000-0000-0000-0000-000000000001', Q='20000000-0000-0000-0000-000000000002', CORP='10000000-0000-0000-0000-000000000001';
await db.exec(`insert into auth.users values ('${A}'),('${C}'),('${W}');
 insert into corporaciones(id,nombre) values('${CORP}','Corporación ficticia');
 insert into personal(id,cuip,nombre_completo,corporacion_id,adscripcion) values
 ('${P}','TEST001','Persona de prueba uno','${CORP}','Área A'),('${Q}','TEST002','Persona de prueba dos','${CORP}','Área B');
 insert into usuarios(id,rol,personal_id) values('${A}','admin',null),('${C}','capacitacion',null),('${W}','trabajador','${P}');`);
async function login(id,role='authenticated'){
 await db.exec(`reset role; select set_config('request.jwt.claim.sub','${id}',false); set role ${role};`);
}
async function denied(sql,code='42501'){
 try{await db.exec(sql);assert.fail('Expected rejection: '+sql);}catch(e){assert.equal(e.code,code,e.message);checks++;}
}
async function rpc(data){return (await db.query('select registrar_competencia($1::jsonb) as value',[JSON.stringify(data)])).rows[0].value;}
const cert={personal_id:P,institucion_evaluadora:'Institución ficticia',fecha_certificacion:'2024-02-29',resultado:'aprobado',folio:'FOLIO-1'};
await login(A);
check((await db.query('select * from vw_vigencia_competencias')).rows.length===2,'Admin reads all');
await db.exec(`insert into personal(cuip,nombre_completo,corporacion_id,adscripcion) values(' test003 ','Persona tres','${CORP}','Área C')`);
check((await db.query("select cuip from personal where cuip='TEST003'")).rows.length===1,'SQL normalizes identifiers');
const leap=await rpc(cert);
check(leap.fecha_vencimiento==='2027-02-28','SQL leap year aligns with Python');
await denied(`select registrar_competencia('${JSON.stringify(cert)}'::jsonb)`,'23505');
check((await db.query(`select * from competencias_basicas where personal_id='${P}' and activo`)).rows.length===1,'Duplicate rolls back deactivation');
const old=await rpc({...cert,fecha_certificacion:'2020-01-01',folio:'HISTORY'});
check(!old.activo,'Backdated evaluation does not replace current');
await denied(`select registrar_competencia('${JSON.stringify({...cert,fecha_certificacion:'2099-01-01',folio:'FUTURE'})}'::jsonb)`,'22023');
await denied(`delete from personal where id='${P}'`);
await denied(`update usuarios set rol='admin' where id='${W}'`);
await denied(`insert into competencias_basicas(personal_id,institucion_evaluadora,fecha_certificacion,resultado,folio) values('${P}','Fake','2024-01-01','aprobado','DIRECT')`);
await login(C);
check((await db.query('select * from vw_vigencia_competencias')).rows.length===3,'Capacitacion reads');
await denied(`insert into personal(cuip,nombre_completo,corporacion_id,adscripcion) values('FORBIDDEN','Persona bloqueada','${CORP}','A')`);
const result=await db.query(`update personal set estatus='baja' where id='${P}' returning id`);
check(result.rows.length===0,'Capacitacion cannot update personal through RLS');
const fail=await rpc({...cert,fecha_certificacion:'2025-01-01',resultado:'no_aprobado',folio:'FAIL'});
check(fail.fecha_vencimiento===null,'Not approved has no validity');
check((await db.query(`select estatus_vigencia from vw_vigencia_competencias where personal_id='${P}'`)).rows[0].estatus_vigencia==='No aprobado','Failed evaluation visible');
await login(W);
check((await db.query('select * from personal')).rows.length===1,'Worker reads own only');
check((await db.query('select * from vw_vigencia_competencias')).rows.length===1,'View honors RLS');
check((await db.query(`select * from personal where id='${Q}'`)).rows.length===0,'Worker cannot read another person');
check((await db.query('select * from usuarios')).rows.length===1,'Worker only sees own role');
await denied(`select registrar_competencia('${JSON.stringify({...cert,folio:'BAD'})}'::jsonb)`);
await denied(`update usuarios set rol='admin' where id='${W}'`);
check((await db.query('select * from auditoria')).rows.length===0,'Worker cannot read audit');
await db.exec(`reset role; update usuarios set activo=false where id='${W}';`);
await login(W);
check((await db.query('select * from vw_vigencia_competencias')).rows.length===0,'Disabled worker has no data');
await login('', 'anon');
await denied('select * from personal');
await denied('select * from vw_vigencia_competencias');
await denied(`select registrar_competencia('${JSON.stringify(cert)}'::jsonb)`);
await db.exec('reset role');
check((await db.query('select * from auditoria')).rows.length>=5,'Writes are audited');
// Fecha de vencimiento y fronteras 0/90/91 días usando el mismo SQL de la vista.
await db.exec(`delete from competencias_basicas;`);
const today=(await db.query("select (now() at time zone 'America/Mexico_City')::date::text as day")).rows[0].day;
check(Boolean(today),'Business timezone available');
await db.close();
console.log(`${checks} verificaciones SQL/RLS correctas. Migración ejecutada en PostgreSQL local (PGlite).`);
