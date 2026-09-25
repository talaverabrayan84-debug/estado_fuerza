import {FormEvent,useEffect,useState} from 'react';
import {Link,useParams} from 'react-router-dom';
import {BookOpen,Plus} from 'lucide-react';
import {api} from '../api';
import {Person,User} from '../types';
import {allPages,dateLabel,ErrorBox,label,Loading,Page,Pager,today,useData} from '../components';
import {Enrollment} from './Training';
import {Evidence} from './Evidence';
type Entry={id:string;personal_id:string;sesion_id:string|null;fecha:string;tipo_actividad:string;descripcion:string;created_at:string;updated_at:string;curso_sesiones:{cursos:{nombre_curso:string}}|null};
export function Journal({user}:{user:User}){
 const {id}=useParams(),own=user.rol==='trabajador'&&user.personal_id===id;
 const [courseOffset,setCourseOffset]=useState(0),[offset,setOffset]=useState(0),[form,setForm]=useState(false),[editing,setEditing]=useState<Entry|undefined>(),[success,setSuccess]=useState('');
 const person=useData<Person>('/personal/'+id),rows=useData<Page<Entry>>(`/personal/${id}/bitacora?offset=${offset}`),enrollments=useData<Page<Enrollment>>(`/personal/${id}/inscripciones?offset=${courseOffset}`);
 if(person.loading)return <Loading/>;if(person.error)return <><ErrorBox message={person.error}/><button className="button secondary" onClick={person.reload}>Reintentar expediente</button></>;
 return <><Link className="back-link" to={'/personal/'+id}>← Volver al expediente</Link><div className="page-heading"><div><span className="eyebrow">SEGUIMIENTO INDIVIDUAL</span><h1>{own?'Mi bitácora':'Bitácora del elemento'}</h1><p>{person.data?.nombre_completo} · Actividades y avances de capacitación.</p></div>{own&&<button className="button primary" onClick={()=>{setEditing(undefined);setForm(!form);}}><Plus size={18}/>Registrar actividad</button>}</div>
 {success&&<div className="success" role="status">{success}</div>}{form&&<JournalForm key={editing?.id??'new'} personId={id!} existing={editing} onCancel={()=>setForm(false)} onSaved={()=>{setForm(false);setSuccess('Actividad guardada en la bitácora.');setOffset(0);rows.reload();}}/>}
 <div className="journal-layout"><section className="table-panel"><div className="panel-heading"><h2>Registro de actividades</h2><BookOpen size={20}/></div><ErrorBox message={rows.error}/>{rows.error&&<button className="text-button" onClick={rows.reload}>Reintentar actividades</button>}{rows.loading?<Loading/>:rows.data?.items.length?<><div className="timeline">{rows.data.items.map(e=><article className="journal-entry" key={e.id}><div className="action-row"><span className="badge">{label(e.tipo_actividad)}</span><span className="muted">{dateLabel(e.fecha)}</span>{own&&<button className="text-button push-right" onClick={()=>{setEditing(e);setForm(true);window.scrollTo({top:0,behavior:'smooth'});}}>Editar</button>}</div><h3>{e.curso_sesiones?.cursos.nombre_curso??'Actividad general'}</h3><p className="journal-text">{e.descripcion}</p><small className="muted">Capturada: {dateLabel(e.created_at)}{e.updated_at!==e.created_at?' · Editada':''}</small><Evidence entryId={e.id} own={own}/></article>)}</div><Pager offset={offset} more={rows.data.has_more} onChange={setOffset}/></>:!rows.error&&<div className="empty"><BookOpen size={30}/><h3>Aún no hay actividades</h3><p>{own?'Registra tu primer avance, entrega u observación.':'Las actividades aparecerán cuando el trabajador las capture.'}</p></div>}</section>
 <aside className="surface journal-courses"><h2>{own?'Mis cursos':'Cursos del elemento'}</h2><ErrorBox message={enrollments.error}/>{enrollments.error&&<button className="text-button" onClick={enrollments.reload}>Reintentar cursos</button>}{enrollments.loading?<Loading/>:enrollments.data?.items.length?enrollments.data.items.map(e=><Link className="journal-course" key={e.id} to={'/cursos/sesiones/'+e.sesion_id}><strong>{e.curso_sesiones.cursos.nombre_curso}</strong><small>{dateLabel(e.curso_sesiones.fecha_inicio)}</small><span>{label(e.estatus)}</span></Link>):!enrollments.error&&<p className="muted">Sin inscripciones registradas.</p>}{enrollments.data&&(courseOffset>0||enrollments.data.has_more)&&<Pager offset={courseOffset} more={enrollments.data.has_more} onChange={setCourseOffset}/>}</aside></div></>;
}
function JournalForm({personId,existing,onSaved,onCancel}:{personId:string;existing?:Entry;onSaved:()=>void;onCancel:()=>void}){
 const [enrollments,setEnrollments]=useState<Enrollment[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState(''),[loaded,setLoaded]=useState(false),[sessionId,setSessionId]=useState(existing?.sesion_id??''),[revision,setRevision]=useState(0);
 useEffect(()=>{const controller=new AbortController();setError('');setLoaded(false);allPages<Enrollment>(`/personal/${personId}/inscripciones`,controller.signal).then(r=>{if(!controller.signal.aborted){setEnrollments(r);setLoaded(true);}}).catch(e=>{if(!controller.signal.aborted)setError(e.message);});return()=>controller.abort();},[personId,revision]);
 async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();const d=Object.fromEntries(new FormData(e.currentTarget));setBusy(true);setError('');try{await api('/bitacora'+(existing?'/'+existing.id:''),{method:existing?'PUT':'POST',body:JSON.stringify({...d,sesion_id:d.sesion_id||null})});onSaved();}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 const unavailable=Boolean(sessionId)&&!enrollments.some(e=>e.sesion_id===sessionId&&e.estatus!=='baja');
 return <form className="surface record-form phase-form" onSubmit={submit} aria-busy={busy||!loaded}><h2>{existing?'Editar actividad':'Nueva actividad'}</h2>
  <div className="form-grid">
   <label>Fecha *<input type="date" name="fecha" required max={today()} defaultValue={existing?.fecha??today()}/></label>
   <label>Tipo de actividad *<select name="tipo_actividad" defaultValue={existing?.tipo_actividad??'avance'}>{['avance','incidencia','entrega','observacion'].map(t=><option value={t} key={t}>{label(t)}</option>)}</select></label>
   <label className="span-two">Sesión relacionada<select name="sesion_id" value={sessionId} onChange={e=>setSessionId(e.target.value)} disabled={!loaded||busy}>
    <option value="">Actividad general, sin sesión</option>
    {sessionId&&!enrollments.some(e=>e.sesion_id===sessionId)&&<option value={sessionId}>Sesión vinculada{loaded?' no disponible':' · Cargando…'}</option>}
    {enrollments.filter(e=>e.estatus!=='baja'||e.sesion_id===existing?.sesion_id).map(e=><option key={e.id} value={e.sesion_id}>{e.curso_sesiones.cursos.nombre_curso} · {dateLabel(e.curso_sesiones.fecha_inicio)}{e.estatus==='baja'?' (inscripción dada de baja)':''}</option>)}
   </select><small>{loaded&&unavailable?'Selecciona una inscripción activa o actividad general para guardar.':'Solo puedes vincular sesiones en las que estás inscrito.'}</small></label>
   <label className="span-two">Descripción *<textarea name="descripcion" rows={5} required minLength={3} maxLength={5000} defaultValue={existing?.descripcion} placeholder="Describe la actividad realizada, el avance o la incidencia."/></label>
  </div><ErrorBox message={error}/>{error&&!loaded&&<button type="button" className="text-button" onClick={()=>setRevision(n=>n+1)}>Reintentar consulta de inscripciones</button>}
  <div className="form-actions"><button className="button secondary" type="button" disabled={busy} onClick={onCancel}>Cancelar</button><button className="button primary" disabled={busy||!loaded||unavailable}>{busy?'Guardando…':'Guardar actividad'}</button></div>
 </form>;
}
