import {createClient} from '@supabase/supabase-js';
export const demo = import.meta.env.VITE_DEMO_MODE === 'true';
const base = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api').replace(/\/$/,'');
const url = import.meta.env.VITE_SUPABASE_URL;
const key = import.meta.env.VITE_SUPABASE_ANON_KEY;
export const supabase = !demo && url && key ? createClient(url,key) : null;
let demoToken = sessionStorage.getItem('ef-demo-session') || '';
export function setDemoToken(token:string) {demoToken=token; token ? sessionStorage.setItem('ef-demo-session',token) : sessionStorage.removeItem('ef-demo-session');}
export async function api<T>(path:string, options:RequestInit={}):Promise<T> {
 const token=demo ? demoToken : (await supabase?.auth.getSession())?.data.session?.access_token;
 let response:Response;
 try { response=await fetch(base+path,{...options,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`} : {}),...options.headers}}); }
 catch {throw new Error('No fue posible conectar con el sistema. Verifique que el servicio esté disponible.');}
 if(!response.ok){
  const payload=await response.json().catch(()=>({detail:'No fue posible completar la operación.'}));
  const detail=Array.isArray(payload.detail)?payload.detail.map((e:{msg:string})=>e.msg.replace('Value error, ','')).join(' '):payload.detail;
  throw new Error(detail || 'No fue posible completar la operación.');
 }
 return response.status===204 ? undefined as T : response.json();
}
