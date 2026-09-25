import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import ts from 'typescript';

// Ejecuta el módulo real con configuración y transporte controlados, sin red.
const source=readFileSync(new URL('../src/api.ts',import.meta.url),'utf8').replaceAll('import.meta.env','__env');
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const validEnv={VITE_DEMO_MODE:'false',VITE_API_URL:'https://api.example.test/api',VITE_SUPABASE_URL:'https://example.supabase.co',VITE_SUPABASE_ANON_KEY:'sb_publishable_example'};
function load(env={},host='app.example.test',transport=async()=>new Response('{}')){
 const exports={},clients=[];
 const client={auth:{getSession:async()=>({data:{session:{access_token:'test-user-token'}}})}};
 const require=()=>({createClient:(...args)=>{clients.push(args);return client;}});
 const storage=new Map();
 const sessionStorage={getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)};
 new Function('exports','require','__env','window','sessionStorage','fetch',compiled)(exports,require,{...validEnv,...env},{location:{hostname:host,origin:`https://${host}`}},sessionStorage,transport);
 return {...exports,clients};
}
test('Supabase real usa solamente configuración pública y el token de sesión',async()=>{
 let called;
 const mod=load({},undefined,async(url,options)=>{called={url,options};return new Response('{"ok":true}');});
 assert.equal(mod.configError,'');assert.equal(mod.clients.length,1);
 assert.deepEqual(await mod.api('/me'),{ok:true});
 assert.equal(called.url,'https://api.example.test/api/me');
 assert.equal(called.options.headers.get('Authorization'),'Bearer test-user-token');
 assert.equal(called.options.headers.get('Content-Type'),null);
});
test('Configuraciones incompletas o inválidas fallan antes de consultar la red',async()=>{
 for(const env of [{VITE_API_URL:''},{VITE_API_URL:'http://127.0.0.1:8000/api'},{VITE_API_URL:'https://user:pass@example.test/api'},{VITE_SUPABASE_URL:'incorrecta'},{VITE_SUPABASE_ANON_KEY:''},{VITE_SUPABASE_ANON_KEY:'sb_secret_example'}]){
  let requests=0;const mod=load(env,undefined,async()=>{requests++;return new Response('{}');});
  assert.ok(mod.configError);assert.equal(mod.clients.length,0);
  await assert.rejects(mod.api('/me'));assert.equal(requests,0);
 }
});
test('Una clave service_role JWT es rechazada, anon es aceptada',()=>{
 const jwt=role=>`eyJhbGciOiJIUzI1NiJ9.${Buffer.from(JSON.stringify({role})).toString('base64url')}.signature`;
 assert.ok(load({VITE_SUPABASE_ANON_KEY:jwt('service_role')}).configError);
 assert.equal(load({VITE_SUPABASE_ANON_KEY:jwt('anon')}).configError,'');
});
test('Demo solo funciona en loopback, nunca en un despliegue remoto',()=>{
 assert.ok(load({VITE_DEMO_MODE:'true'}).configError);
 const local=load({VITE_DEMO_MODE:'true',VITE_API_URL:''},'127.0.0.1');
 assert.equal(local.demo,true);assert.equal(local.configError,'');assert.equal(local.supabase,null);
 assert.equal(load({VITE_API_URL:'/api'}).configError,'');
});
test('Carga multipart conserva el boundary generado por el navegador',async()=>{
 let headers;const mod=load({},undefined,async(_,options)=>{headers=options.headers;return new Response('{}');});
 const data=new FormData();data.append('destino','personal');
 await mod.api('/carga-masiva/previsualizar',{method:'POST',body:data});
 assert.equal(headers.get('Content-Type'),null);
 await mod.api('/cursos',{method:'POST',body:'{}'});
 assert.equal(headers.get('Content-Type'),'application/json');
});
test('Una cancelación conserva AbortError y errores HTTP ofrecen detalle legible',async()=>{
 const controller=new AbortController();controller.abort();
 const cancelled=load({},undefined,async()=>{throw new DOMException('Cancelado','AbortError');});
 await assert.rejects(cancelled.api('/me',{signal:controller.signal}),{name:'AbortError'});
 const invalid=load({},undefined,async()=>new Response(JSON.stringify({detail:[{msg:'Value error, Fecha inválida.'}]}),{status:422}));
 await assert.rejects(invalid.api('/cursos'),{message:'Fecha inválida.'});
});
