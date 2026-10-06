import {CSSProperties,FormEvent,useEffect,useRef,useState} from 'react';
import {Link,useSearchParams} from 'react-router-dom';
import {Bell,BookOpen,Check} from 'lucide-react';
import {api} from '../api';
import {dateLabel,ErrorBox,Loading,today} from '../components';

type Value=string|number|null;
type Cell={key:string;col:string;row:number;span:[number,number];kind:'date'|'number'|'text';format:string;label:Value;style:CSSProperties};
type Delivery={key:string;fund:string;course:string;due:string|null;days:number|null;status:string;received:string|null;source_received:boolean};
type Sheet={fund:string;version:number;data:{values:Record<string,Value>;receipts:Record<string,string|null>};layout:{name:string;header:number;due_col:string;widths:number[];heights:number[];rows:Cell[][]};deliveries:Delivery[]};
type Alerts={items:Delivery[];missing_dates:number;as_of:string};
const statuses:Record<string,string>={recibida:'Recibida',sin_fecha:'Sin fecha de entrega',vencida:'Entrega vencida',hoy:'Entrega hoy','1_dia':'Entrega mañana','3_dias':'Entrega en 3 días o menos','7_dias':'Entrega en 7 días o menos',programada:'Programada'};
const datePattern=/^\d{4}-\d{2}-\d{2}$/;
function display(v:Value,format?:string){if(typeof v==='string'&&datePattern.test(v)){const [year,month,day]=v.split('-');if(format==='mm-dd-yy')return `${month}-${day}-${year.slice(-2)}`;return dateLabel(v);}return v??'';}

function useFundingBook(){
 const [data,setData]=useState<{sheets:Sheet[]}|null>(null),[error,setError]=useState(''),[revision,setRevision]=useState(0);
 useEffect(()=>{let controller:AbortController|undefined;
  const refresh=()=>{controller?.abort();controller=new AbortController();const signal=controller.signal;
   api<{sheets:Sheet[]}>('/bitacora-fondos',{signal}).then(r=>{if(!signal.aborted){setData(r);setError('');}}).catch(e=>{if(!signal.aborted)setError(e.message);});};
  refresh();const timer=setInterval(refresh,60000);window.addEventListener('focus',refresh);
  return()=>{clearInterval(timer);controller?.abort();window.removeEventListener('focus',refresh);};
 },[revision]);
 return {data,error,loading:!data&&!error,reload:()=>setRevision(n=>n+1)};
}

export function FundingNotice(){
 const [state,setState]=useState<Alerts|null>(null),[error,setError]=useState('');
 useEffect(()=>{
  let controller:AbortController|undefined;
  const refresh=()=>{controller?.abort();controller=new AbortController();const signal=controller.signal;
   api<Alerts>('/bitacora-fondos/alertas',{signal}).then(r=>{if(!signal.aborted){setState(r);setError('');}}).catch(e=>{if(!signal.aborted)setError(e.message);});};
  refresh();const timer=setInterval(refresh,60000);window.addEventListener('focus',refresh);
  const changed=()=>refresh();window.addEventListener('funding-changed',changed);
  return()=>{clearInterval(timer);controller?.abort();window.removeEventListener('focus',refresh);window.removeEventListener('funding-changed',changed);};
 },[]);
 return <div className="funding-notice" role="status" aria-live="polite"><Bell size={18}/>{error?<span>No se pudieron actualizar las alertas UMS. <Link to="/bitacora-fondos">Consultar bitácora</Link></span>:!state?<span>Consultando entregas UMS…</span>:<Link to="/bitacora-fondos">{state.items.length?`${state.items.length} entrega${state.items.length===1?'':'s'} UMS próxima${state.items.length===1?'':'s'} o vencida${state.items.length===1?'':'s'}`:'Sin entregas UMS próximas ni vencidas'}{state.missing_dates>0?` · ${state.missing_dates} sin fecha`:''}</Link>}</div>;
}

export function FundingJournal(){
 const [params,setParams]=useSearchParams(),[fund,setFund]=useState(params.get('fund')==='FOFISP'?'FOFISP':'FASP');
 const book=useFundingBook();
 const [edit,setEdit]=useState<{sheet:Sheet;cell:Cell;section:'values'|'receipts'}|null>(null),[message,setMessage]=useState('');
 const [zoom,setZoom]=useState(.75),[error,setError]=useState('');
 const tableRef=useRef<HTMLDivElement>(null);
 const sheet=book.data?.sheets.find(s=>s.fund===fund);
 useEffect(()=>{const f=params.get('fund');if(f==='FASP'||f==='FOFISP')setFund(f);},[params]);
 useEffect(()=>{if(sheet&&tableRef.current&&!params.get('delivery')){tableRef.current.scrollTop=sheet.layout.heights.slice(0,sheet.layout.header-1).reduce((a,b)=>a+b,0)*zoom;tableRef.current.scrollLeft=0;}},[sheet?.fund,zoom]);
 useEffect(()=>{if(sheet&&params.get('delivery'))tableRef.current?.querySelector(`[data-cell="${params.get('delivery')?.replace(/[^A-Z0-9]/g,'')}"]`)?.scrollIntoView({block:'center',inline:'center',behavior:'smooth'});},[sheet,params]);
 function saved(){setEdit(null);setMessage('Cambios guardados. Las alertas UMS se actualizaron.');book.reload();window.dispatchEvent(new Event('funding-changed'));}
 function select(f:string){setFund(f);setParams({fund:f});setMessage('');setEdit(null);}
 return <><div className="page-heading"><div><span className="eyebrow">SEGUIMIENTO INSTITUCIONAL</span><h1>Bitácora FASP y FOFISP</h1><p>Control de cursos, validaciones, metas y entregables de la UMS.</p></div><BookOpen size={28}/></div>
  {message&&<div className="success" role="status"><Check size={18}/>{message}</div>}<ErrorBox message={book.error||error}/>
  <div className="funding-toolbar"><div className="funding-tabs" aria-label="Fondo de capacitación">{['FASP','FOFISP'].map(f=><button key={f} className={'button '+(fund===f?'primary':'secondary')} aria-pressed={fund===f} onClick={()=>select(f)}>{f} 2026</button>)}</div><label>Vista<select value={zoom} onChange={e=>setZoom(Number(e.target.value))}><option value={.75}>75 %</option><option value={1}>100 %</option></select></label><button className="button secondary" onClick={()=>{setError('');book.reload();}}>Actualizar</button></div>
  {book.loading?<Loading/>:sheet&&<>
   <section className="table-panel"><div className="panel-heading"><h2>Formato de la bitácora {fund}</h2><span className="muted">Selecciona una celda para editar</span></div>
    <div className="funding-grid-scroll" ref={tableRef} tabIndex={0} aria-label="Bitácora con desplazamiento horizontal y vertical"><table className="funding-grid" style={{width:sheet.layout.widths.reduce((a,b)=>a+b,0)*zoom}}>
     <caption className="sr-only">Bitácora {fund} 2026 con los encabezados y celdas combinadas del archivo de referencia</caption>
     <colgroup>{sheet.layout.widths.map((w,i)=><col key={i} style={{width:w*zoom}}/>)}</colgroup>
     <thead>{sheet.layout.rows.slice(0,sheet.layout.header).map((row,i)=><tr key={i} style={{height:sheet.layout.heights[i]*zoom}}>{row.map(c=><th key={c.key} rowSpan={c.span[0]} colSpan={c.span[1]} style={{...c.style,fontSize:Number(c.style.fontSize)*zoom}}>{display(c.label,c.format)}</th>)}</tr>)}</thead>
     <tbody>{sheet.layout.rows.slice(sheet.layout.header).map((row,i)=><tr key={i} style={{height:sheet.layout.heights[i+sheet.layout.header]*zoom}}>{row.map(c=><td key={c.key} data-cell={c.key} rowSpan={c.span[0]} colSpan={c.span[1]} className={params.get('delivery')===c.key?'funding-target':''} style={{...c.style,fontSize:Number(c.style.fontSize)*zoom}}><button className="funding-cell" aria-label={`Editar ${c.key}: ${sheet.data.values[c.key]??'sin capturar'}`} onClick={()=>{setMessage('');setEdit({sheet,cell:c,section:'values'});}}>{display(sheet.data.values[c.key],c.format)||<span className="funding-blank">—</span>}</button></td>)}</tr>)}</tbody>
    </table></div></section>
   <p className="footnote">Las alertas se actualizan cada minuto. Captura la fecha de entrega UMS en la columna {sheet.layout.due_col} y registra la recepción completa para cerrar el seguimiento.</p>
   <section className="table-panel funding-deliveries"><div className="panel-heading"><div><h2>Alertas y recepción de entregables UMS</h2><p className="muted">Avisos a 7, 3 y 1 días, el día de entrega y después del vencimiento.</p></div></div><div className="table-scroll"><table><thead><tr><th>Curso</th><th>Fecha de entrega</th><th>Seguimiento UMS</th><th>Recepción completa</th></tr></thead><tbody>{sheet.deliveries.map(d=><tr key={d.key}><td><button className="text-button" onClick={()=>setParams({fund,delivery:d.key})}>{d.course}</button></td><td>{d.due?dateLabel(d.due):'Sin fecha'}{d.days!==null&&!d.source_received&&!d.received&&<small>{d.days<0?`${-d.days} días de retraso`:d.days===0?'Entrega hoy':`Faltan ${d.days} días`}</small>}</td><td><span className={'badge funding-status-'+d.status}>{statuses[d.status]}</span></td><td>{d.received&&<small>Recibida: {dateLabel(d.received)}</small>}{d.source_received&&<small>Entrega registrada en la bitácora</small>}<button className="text-button" onClick={()=>{const cell=sheet.layout.rows.flat().find(c=>c.key===d.key)!;setEdit({sheet,cell,section:'receipts'});}}>{d.received?'Editar recepción':'Registrar recepción'}</button></td></tr>)}</tbody></table></div></section>
  </>}
  {book.error&&<button className="button secondary" onClick={book.reload}>Reintentar</button>}
  {edit&&<CellEditor key={edit.sheet.fund+edit.cell.key+edit.section} {...edit} onCancel={()=>setEdit(null)} onSaved={saved} onConflict={()=>{book.reload();}}/>}
 </>;
}

function CellEditor({sheet,cell,section,onCancel,onSaved,onConflict}:{sheet:Sheet;cell:Cell;section:'values'|'receipts';onCancel:()=>void;onSaved:()=>void;onConflict:()=>void}){
 const original=section==='receipts'?sheet.data.receipts[cell.key]:sheet.data.values[cell.key];
 const isDate=section==='receipts'||cell.kind==='date';
 const [value,setValue]=useState(String(original??'')),[mode,setMode]=useState(original==='N/A'?'N/A':original==='ENTREGADO'?'ENTREGADO':'date');
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[conflict,setConflict]=useState(false);
 const dialogRef=useRef<HTMLDialogElement>(null);
 useEffect(()=>{const dialog=dialogRef.current;dialog?.showModal();return()=>dialog?.close();},[]);
 async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();setBusy(true);setError('');const fields=new FormData(e.currentTarget),raw=String(fields.get('value')??''),selectedMode=String(fields.get('mode')??'date');let v:Value=raw||null;
  if(isDate&&section==='values'&&selectedMode!=='date')v=selectedMode;
  else if(!isDate&&cell.kind==='number'&&raw.trim()!==''&&Number.isFinite(Number(raw)))v=Number(raw);
  try{await api(`/bitacora-fondos/${sheet.fund}`,{method:'PUT',body:JSON.stringify({version:sheet.version,section,key:cell.key,value:v})});onSaved();}
  catch(e){const msg=(e as Error).message;setError(msg);if(msg.includes('cambió')){setConflict(true);onConflict();}}
  finally{setBusy(false);}}
 return <dialog className="funding-dialog" ref={dialogRef} onCancel={e=>{e.preventDefault();if(!busy)onCancel();}}><form onSubmit={submit}><h2>{section==='receipts'?'Recepción completa de entregables UMS':`Editar ${sheet.fund} · ${cell.key}`}</h2>
  {section==='receipts'?<p>Registra la fecha en que se recibió la entrega completa. Una entrega parcial conserva la alerta. Para reabrir el seguimiento, borra esta fecha y cualquier marca de entrega en la bitácora.</p>:<p>La edición conserva el formato y la agrupación de la celda.</p>}
  {isDate&&section==='values'&&<label>Contenido<select name="mode" value={mode} onChange={e=>{setMode(e.target.value);if(e.target.value==='date'&&!datePattern.test(value))setValue('');}}><option value="date">Fecha</option><option value="N/A">N/A</option><option value="ENTREGADO">ENTREGADO</option></select></label>}
  {isDate&&(section==='receipts'||mode==='date')?<label>{section==='receipts'?'Fecha de recepción completa':'Fecha'}<input autoFocus type="date" name="value" value={datePattern.test(value)?value:''} max={section==='receipts'?today():undefined} onChange={e=>setValue(e.target.value)}/></label>:!isDate&&<label>Contenido<textarea name="value" autoFocus rows={5} maxLength={5000} value={value} onChange={e=>setValue(e.target.value)}/></label>}
  <ErrorBox message={error}/><div className="form-actions"><button type="button" className="button secondary" disabled={busy} onClick={onCancel}>{conflict?'Cerrar y revisar cambios':'Cancelar'}</button><button className="button primary" disabled={busy||conflict}>{busy?'Guardando…':'Guardar'}</button></div>
 </form></dialog>;
}
