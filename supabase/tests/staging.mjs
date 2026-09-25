// Supabase service schemas are stubs here. This checks SQL, not HTTP/Auth/Storage.
import {createRequire} from 'node:module';
import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const require=createRequire(new URL('../../frontend/package.json',import.meta.url));
const {PGlite}=require('@electric-sql/pglite');
const db=new PGlite();
const sql=async path=>readFile(new URL('../'+path,import.meta.url),'utf8');
await db.exec(`create role anon nologin; create role authenticated nologin; create schema auth;
create table auth.users(id uuid primary key);
create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
grant usage on schema auth to authenticated,anon; grant execute on function auth.uid() to authenticated,anon;
create schema storage;
create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);
create table storage.objects(id uuid primary key default gen_random_uuid(),bucket_id text,name text);
alter table storage.objects enable row level security;
grant usage on schema storage to authenticated,anon;
grant select,insert,delete on storage.objects to authenticated;`);
for(const f of ['001_fase1.sql','002_fase2.sql','003_evidencias.sql'])await db.exec(await sql('migrations/'+f));
await db.exec(await sql('seed_staging.sql'));
const snapshot=async()=> (await db.query(`select
 (select count(*) from personal) as people,
 (select count(*) from competencias_basicas) as evaluations,
 (select count(*) from cursos) as courses,
 (select count(*) from curso_sesiones) as sessions,
 (select count(*) from inscripciones) as enrollments,
 (select count(*) from auditoria) as audits,
 (select count(*) from usuarios) as profiles,
 (select count(*) from auth.users) as accounts`)).rows[0];
const first=await snapshot();
assert.equal(first.people,5);assert.equal(first.evaluations,4);
assert.equal(first.courses,2);assert.equal(first.sessions,3);assert.equal(first.enrollments,2);
assert.equal(first.profiles,0);assert.equal(first.accounts,0);
assert.deepEqual(new Set((await db.query('select estatus_vigencia from vw_vigencia_competencias')).rows.map(r=>r.estatus_vigencia)),
 new Set(['Vigente','Por vencer','Vencida','No aprobado','Sin registro']));
await db.exec(await sql('seed_staging.sql'));
assert.deepEqual(await snapshot(),first,'Second seed must not change data or audits');
const results=await db.exec(await sql('verify_staging.sql'));
const checks=results.flatMap(r=>r.rows).filter(r=>'comprobacion' in r);
assert.ok(checks.length>30);
assert.deepEqual(checks.filter(r=>!r.correcto),[],'Postmigration verification failures');
await db.close();
console.log(`Seed idempotente sin cuentas Auth; cinco estados comprobados y ${checks.length} comprobaciones postmigración correctas.`);
