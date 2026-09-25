import {useEffect,useState} from 'react';
import {api} from './api';
export type Page<T>={items:T[];has_more:boolean};
export function useData<T>(path:string){
 const [rev,setRev]=useState(0);
 const [result,setResult]=useState<{path:string;rev:number;data:T|null;error:string}|null>(null);
 useEffect(()=>{
  const controller=new AbortController();
  api<T>(path,{signal:controller.signal}).then(data=>{
   if(!controller.signal.aborted)setResult({path,rev,data,error:''});
  }).catch(e=>{
   if(!controller.signal.aborted)setResult({path,rev,data:null,error:e.message});
  });
  return()=>controller.abort();
 },[path,rev]);
 const current=result?.path===path&&result.rev===rev?result:null;
 return {data:current?.data??null,error:current?.error??'',loading:!current,reload:()=>setRev(r=>r+1)};
}
export async function allPages<T>(path:string,signal?:AbortSignal):Promise<T[]>{
 const items:T[]=[];let offset=0;
 for(;;){const p=await api<Page<T>>(`${path}${path.includes('?')?'&':'?'}offset=${offset}&limit=100`,{signal});items.push(...p.items);if(!p.has_more)return items;offset+=100;}
}
export function ErrorBox({message}:{message:string}){return message?<div role="alert" className="error">{message}</div>:null;}
export function Loading(){return <div className="loading" role="status">Cargando información…</div>;}
export function Pager({offset,more,onChange,disabled=false}:{offset:number;more:boolean;onChange:(n:number)=>void;disabled?:boolean}){return <div className="pagination"><span>Página {offset/25+1}</span><div><button type="button" className="button secondary" disabled={disabled||!offset} onClick={()=>onChange(Math.max(0,offset-25))}>Anterior</button><button type="button" className="button secondary" disabled={disabled||!more} onClick={()=>onChange(offset+25)}>Siguiente</button></div></div>;}
export function today(){const p=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Mexico_City',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());return ['year','month','day'].map(t=>p.find(x=>x.type===t)?.value).join('-');}
export function dateLabel(s:string){const timestamp=s.includes('T');return new Intl.DateTimeFormat('es-MX',{day:'numeric',month:'short',year:'numeric',timeZone:timestamp?'America/Mexico_City':'UTC'}).format(new Date(timestamp?s:s+'T12:00:00Z'));}
const labels:Record<string,string>={formacion_inicial:'Formación inicial',competencias_basicas:'Competencias básicas',actualizacion:'Actualización',en_linea:'En línea',observacion:'Observación',revision:'En revisión',confirmada:'Confirmada',recurso_propio:'Recurso propio'};
export function label(s:string){return labels[s]??s.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());}
