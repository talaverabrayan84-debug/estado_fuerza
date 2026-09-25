import {createClient, SupabaseClient} from '@supabase/supabase-js';
const loopback = (host:string) => ['localhost','127.0.0.1','[::1]'].includes(host);
const requestedDemo = import.meta.env.VITE_DEMO_MODE === 'true';
export const demo = requestedDemo && loopback(window.location.hostname);
const base = (import.meta.env.VITE_API_URL?.trim() || (demo?'http://127.0.0.1:8000/api':'')).replace(/\/$/,'');
const url = import.meta.env.VITE_SUPABASE_URL?.trim();
const key = import.meta.env.VITE_SUPABASE_ANON_KEY?.trim();
let configurationError = '';
let client:SupabaseClient|null = null;
try {
 if(requestedDemo&&!demo)throw new Error('La demostración solo está disponible en el equipo local. Configura VITE_DEMO_MODE=false para este entorno.');
 if(!base)throw new Error('Falta configurar VITE_API_URL para conectar con el servicio del sistema.');
 const apiUrl=new URL(base,window.location.origin);
 if(!['http:','https:'].includes(apiUrl.protocol)||apiUrl.username||apiUrl.password||apiUrl.search||apiUrl.hash||(!loopback(window.location.hostname)&&loopback(apiUrl.hostname))||(apiUrl.protocol!=='https:'&&!loopback(apiUrl.hostname)))throw new Error('VITE_API_URL debe ser una dirección HTTPS del servicio, o una ruta del mismo sitio.');
 if(!demo){
  if(!url||!key)throw new Error('Falta configurar la conexión pública con Supabase. Consulte la guía de instalación.');
  const authUrl=new URL(url);
  if(authUrl.protocol!=='https:'||authUrl.username||authUrl.password||authUrl.search||authUrl.hash)throw new Error('VITE_SUPABASE_URL debe ser la dirección HTTPS del proyecto Supabase.');
  if(key.startsWith('sb_secret_'))throw new Error('La conexión del navegador requiere una clave pública de Supabase.');
  // Las claves JWT antiguas también deben tener el rol público anon.
  if(key.split('.').length===3){
   const payload=JSON.parse(atob(key.split('.')[1].replaceAll('-','+').replaceAll('_','/')));
   if(payload.role!=='anon')throw new Error('La conexión del navegador requiere una clave pública de Supabase.');
  }
  client=createClient(url,key);
 }
} catch(e) {configurationError=e instanceof Error?e.message:'La configuración de conexión no es válida.';}
export const configError=configurationError;
export const supabase=client;
let demoToken = sessionStorage.getItem('ef-demo-session') || '';
export function setDemoToken(token:string) {demoToken=token; token ? sessionStorage.setItem('ef-demo-session',token) : sessionStorage.removeItem('ef-demo-session');}
async function request(path:string, options:RequestInit={}):Promise<Response> {
 if(configError)throw new Error(configError);
 const token=demo ? demoToken : (await supabase?.auth.getSession())?.data.session?.access_token;
 let response:Response;
 const headers=new Headers(options.headers);
 if(options.body&&!(options.body instanceof FormData)&&!headers.has('Content-Type'))headers.set('Content-Type','application/json');
 if(token)headers.set('Authorization',`Bearer ${token}`);
 try { response=await fetch(base+path,{...options,headers}); }
 catch(e) {if(options.signal?.aborted)throw e;throw new Error('No fue posible conectar con el sistema. Verifique que el servicio esté disponible.');}
 if(!response.ok){
  const payload=await response.json().catch(()=>({detail:'No fue posible completar la operación.'}));
  const detail=Array.isArray(payload.detail)?payload.detail.map((e:{msg:string})=>e.msg.replace('Value error, ','')).join(' '):payload.detail;
  throw new Error(detail || 'No fue posible completar la operación.');
 }
 return response;
}
export async function api<T>(path:string, options:RequestInit={}):Promise<T> {
 const response=await request(path,options);
 return response.status===204 ? undefined as T : response.json();
}
export async function download(path:string,name:string) {
 const response=await request(path),url=URL.createObjectURL(await response.blob());
 const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(url),1000);
}
