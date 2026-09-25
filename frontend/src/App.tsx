import {createContext, FormEvent, useContext, useEffect, useRef, useState} from 'react';
import {Link, NavLink, Navigate, Route, Routes, useLocation, useNavigate, useParams} from 'react-router-dom';
import {ArrowLeft, ArrowRight, Bell, Check, ChevronLeft, ChevronRight, CircleAlert, ClipboardCheck, FileText, LogOut, Plus, Search, ShieldCheck, Users} from 'lucide-react';
import {api, configError, demo, setDemoToken, supabase} from './api';
import {Catalogs, Evaluation, Person, Role, roleLabels, states, User} from './types';
import {Calendar,SessionDetail} from './pages/Training';
import {Journal} from './pages/Journal';
import {Imports} from './pages/Imports';
import {useData} from './components';

const Auth = createContext<User|null>(null);
function useUser(){return useContext(Auth)!;}
function formatDate(value:string|null){return value?new Intl.DateTimeFormat('es-MX',{day:'2-digit',month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(value+'T12:00:00Z')):'—';}
function today(){const p=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Mexico_City',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()); return ['year','month','day'].map(t=>p.find(x=>x.type===t)?.value).join('-');}
function initials(value:string){return value.split(' ').filter(Boolean).slice(0,2).map(s=>s[0]).join('');}
function Badge({value}:{value:string}){return <span className={'badge status-'+value.toLowerCase().replaceAll(' ','-')}>{value}</span>;}
function ErrorBox({message}:{message:string}){return message?<div role="alert" className="error"><CircleAlert size={18}/><span>{message}</span></div>:null;}
function Loading(){return <div className="loading" role="status">Cargando información…</div>;}

export default function App(){
 const location=useLocation();
 const [user,setUser]=useState<User|null>(null),[ready,setReady]=useState(false);
 const authGeneration=useRef(0);
 useEffect(()=>{
  let mounted=true;
  const load=()=>{const generation=++authGeneration.current;return api<User>('/me').then(u=>{if(mounted&&generation===authGeneration.current)setUser(u);}).catch(()=>{if(mounted&&generation===authGeneration.current)setUser(null);}).finally(()=>{if(mounted&&generation===authGeneration.current)setReady(true);});};
  load();
  const subscription=supabase?.auth.onAuthStateChange((event)=>{if(event==='SIGNED_OUT'){authGeneration.current++;setUser(null);setReady(true);}else if(['SIGNED_IN','TOKEN_REFRESHED','USER_UPDATED'].includes(event)){const generation=authGeneration.current;queueMicrotask(()=>{if(mounted&&generation===authGeneration.current)void load();});}});
  return()=>{mounted=false;subscription?.data.subscription.unsubscribe();};
 },[]);
 async function logout(){authGeneration.current++;setReady(false);setUser(null);try{if(demo)await api('/demo/session',{method:'DELETE'});else await supabase?.auth.signOut({scope:'local'});}catch{/* La sesión local se limpia aunque el servicio no responda. */}finally{authGeneration.current++;setDemoToken('');setUser(null);setReady(true);}}
 if(!ready)return <Loading/>;
 if(!user)return <Login onLogin={u=>{authGeneration.current++;setUser(u);}}/>;
 const worker=user.rol==='trabajador';
 return <Auth.Provider value={user}><div className="shell">
  <aside className="sidebar"><Link className="brand" to="/"><span className="brand-icon"><ShieldCheck size={25}/></span><span>Estado de Fuerza<small>Gestión de capacitación</small></span></Link>
   <div className="sidebar-label">ESPACIO DE TRABAJO</div>
   <nav aria-label="Navegación principal">{worker?<NavLink end to={`/personal/${user.personal_id}`}><FileText size={20}/>Mi expediente</NavLink>:<><NavLink to="/estado-fuerza"><Users size={20}/>Estado de fuerza</NavLink><NavLink to="/alertas"><Bell size={20}/>Vigencia y alertas</NavLink></>}<NavLink to="/cursos"><ClipboardCheck size={20}/>Calendario de cursos</NavLink>{worker&&<NavLink to={`/personal/${user.personal_id}/bitacora`}><FileText size={20}/>Mi bitácora</NavLink>}{user.rol==='admin'&&<NavLink to="/carga-masiva"><Plus size={20}/>Carga masiva</NavLink>}</nav>
   <div className="sidebar-note"><ClipboardCheck size={24}/><strong>Formación y seguimiento</strong><p>Organiza los cursos y consulta los avances de capacitación del personal.</p><span>Segunda fase</span></div>
   <div className="account"><div className="avatar">{initials(roleLabels[user.rol])}</div><div><strong>{roleLabels[user.rol]}</strong><small title={user.email}>{user.email}</small></div><button aria-label="Cerrar sesión" title="Cerrar sesión" className="icon-button" onClick={logout}><LogOut size={19}/></button></div>
  </aside>
  <div className="main-area"><header className="topbar"><span>Sistema de Gestión del Estado de Fuerza</span><span className="topbar-label">{roleLabels[user.rol]}</span></header>
   {demo&&<div className="demo-banner"><CircleAlert size={16}/><span>Demostración local · Datos ficticios. Los cambios se reinician al detener el servicio.</span></div>}
   <main><Routes key={`${user.id}:${user.rol}:${location.pathname}`}>
    <Route path="/" element={<Navigate to={worker?`/personal/${user.personal_id}`:'/estado-fuerza'} replace/>}/>
    <Route path="/estado-fuerza" element={worker?<Navigate to="/" replace/>:<Roster/>}/>
    <Route path="/alertas" element={worker?<Navigate to="/" replace/>:<Roster alerts/>}/>
    <Route path="/personal/nuevo" element={user.rol==='admin'?<PersonForm/>:<Navigate to="/" replace/>}/>
    <Route path="/personal/:id/editar" element={user.rol==='admin'?<EditPerson/>:<Navigate to="/" replace/>}/>
    <Route path="/personal/:id" element={<Detail/>}/>
    <Route path="/cursos" element={<Calendar user={user}/>}/>
    <Route path="/cursos/sesiones/:id" element={<SessionDetail user={user}/>}/>
    <Route path="/personal/:id/bitacora" element={<Journal user={user}/>}/>
    <Route path="/carga-masiva" element={user.rol==='admin'?<Imports/>:<Navigate to="/" replace/>}/>
    <Route path="*" element={<Navigate to="/" replace/>}/>
   </Routes></main>
  </div></div></Auth.Provider>;
}

function Login({onLogin}:{onLogin:(u:User)=>void}){
 const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[role,setRole]=useState<Role>('admin'),[busy,setBusy]=useState(false),[error,setError]=useState('');
 async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError('');try{
  if(demo){const s=await api<{access_token:string}>('/demo/session',{method:'POST',body:JSON.stringify({role})});setDemoToken(s.access_token);}
  else{if(!supabase)throw new Error('Falta configurar la conexión con Supabase. Consulte la guía de instalación.'); const {error}=await supabase.auth.signInWithPassword({email,password});if(error)throw new Error('No se pudo iniciar sesión. Verifique sus credenciales y vuelva a intentar.');}
  onLogin(await api<User>('/me'));
 }catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 return <div className="login-page"><section className="login-context"><div className="brand"><span className="brand-icon"><ShieldCheck size={30}/></span><span>Estado de Fuerza<small>Gestión de capacitación</small></span></div><div><span className="eyebrow light">SEGUIMIENTO DE COMPETENCIAS</span><h1>La información de tu personal,<br/>en un mismo lugar.</h1><p>Consulta expedientes, organiza cursos y da seguimiento a la capacitación del personal.</p></div><span className="login-footer">Estado de fuerza · Segunda fase</span></section><section className="login-form"><div className="login-form-inner"><span className="eyebrow">ACCESO AL SISTEMA</span><h2>{demo?'Explora el sistema':'Iniciar sesión'}</h2><p className="muted">{demo?'Selecciona un perfil para recorrer el sistema con datos ficticios.':'Ingresa con la cuenta habilitada por tu administrador.'}</p><form onSubmit={submit}>
  {demo?<label>Perfil de demostración<select value={role} onChange={e=>setRole(e.target.value as Role)}>{Object.entries(roleLabels).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>:<><label>Correo electrónico<input type="email" autoComplete="username" value={email} onChange={e=>setEmail(e.target.value)} required/></label><label>Contraseña<input type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required/></label></>}
  <ErrorBox message={configError||error}/><button className="button primary wide" disabled={busy||Boolean(configError)}>{busy?'Ingresando…':demo?'Entrar a la demostración':'Iniciar sesión'}<ArrowRight size={18}/></button></form>
  {demo?<p className="footnote">Entorno de prueba sin conexión a Supabase. No captures información real.</p>:<p className="footnote">Si no tienes acceso, contacta al administrador del sistema.</p>}
 </div></section></div>;
}

function Roster({alerts=false}:{alerts?:boolean}){
 const user=useUser();
 const [q,setQ]=useState(''),[search,setSearch]=useState(''),[status,setStatus]=useState('activo'),[corp,setCorp]=useState(''),[vig,setVig]=useState(alerts?'Vencida':''),[offset,setOffset]=useState(0);
 useEffect(()=>{setVig(alerts?'Vencida':'');setOffset(0);},[alerts]);
 useEffect(()=>{const timeout=setTimeout(()=>{setSearch(q);setOffset(0);},250);return()=>clearTimeout(timeout);},[q]);
 const catalog=useData<Catalogs>('/catalogos'), summary=useData<Record<string,number>>('/alertas/resumen'), config=useData<{dias_alerta:number}>('/configuracion');
 const query=new URLSearchParams({q:search,estatus:status,vigencia:vig,offset:String(offset),limit:'25'});if(corp)query.set('corporacion_id',corp);
 const rows=useData<{items:Person[];has_more:boolean}>('/personal?'+query);
 function filter(fn:()=>void){fn();setOffset(0);}
 return <><div className="page-heading"><div><span className="eyebrow">{alerts?'CONTROL DE VIGENCIA':'DIRECTORIO DE PERSONAL'}</span><h1>{alerts?'Vigencia y alertas':'Estado de fuerza'}</h1><p>{alerts?`Anticipa las recertificaciones. La alerta preventiva considera ${config.data?.dias_alerta??90} días.`:'Consulta expedientes y da seguimiento a las competencias básicas.'}</p></div>{user.rol==='admin'&&<Link className="button primary" to="/personal/nuevo"><Plus size={19}/>Registrar elemento</Link>}</div>
  <div className="summary-heading"><strong>Personal activo</strong><span>{summary.data?`${summary.data.total} elementos`:'Consultando…'}</span></div>
  <ErrorBox message={summary.error}/>
  <section className="stats" aria-label="Resumen de vigencia del personal activo">{states.map(s=><button key={s} className={'stat '+(vig===s?'selected':'')} onClick={()=>filter(()=>{setVig(vig===s?'':s);setStatus('activo');})}><span className={'stat-label status-text-'+s.toLowerCase().replaceAll(' ','-')}>{s}</span><strong>{summary.data?.[s]??'—'}</strong><span className="stat-caption">{s==='Sin registro'?'Sin evaluación capturada':s==='No aprobado'?'Requiere seguimiento':s==='Vencida'?'Fecha de vigencia superada':s==='Por vencer'?'Dentro del periodo de alerta':'Fuera del periodo de alerta'}</span></button>)}</section>
  <section className="table-panel"><div className="panel-heading"><h2>{alerts?'Seguimiento de competencias':'Directorio del estado de fuerza'}</h2>{vig&&<button className="text-button" onClick={()=>filter(()=>setVig(''))}>Quitar filtro: {vig} ×</button>}</div>
   <div className="filters"><label className="search-label"><span>Buscar personal</span><div className="search-input"><Search size={18}/><input placeholder="Nombre, CUIP o CURP" value={q} onChange={e=>setQ(e.target.value)}/></div></label><label>Corporación<select value={corp} onChange={e=>filter(()=>setCorp(e.target.value))}><option value="">Todas las corporaciones</option>{catalog.data?.corporaciones.map(c=><option value={c.id} key={c.id}>{c.nombre}</option>)}</select></label><label>Situación del personal<select value={status} onChange={e=>filter(()=>setStatus(e.target.value))}><option value="">Todas las situaciones</option>{['activo','baja','comisionado','licencia'].map(s=><option key={s} value={s}>{s[0].toUpperCase()+s.slice(1)}</option>)}</select></label><label>Vigencia<select value={vig} onChange={e=>filter(()=>setVig(e.target.value))}><option value="">Todos los estados</option>{states.map(s=><option key={s}>{s}</option>)}</select></label></div>
   <ErrorBox message={catalog.error||rows.error}/>{rows.error&&<button className="button secondary" onClick={rows.reload}>Reintentar</button>}
   {rows.loading?<Loading/>:rows.data?.items.length?<><div className="table-scroll"><table><thead><tr><th>Elemento</th><th>Corporación / adscripción</th><th>Vigencia de competencias</th><th>Vencimiento</th><th><span className="sr-only">Acciones</span></th></tr></thead><tbody>{rows.data.items.map(p=><tr key={p.personal_id}><td><Link className="person-cell" to={`/personal/${p.personal_id}`}><span className="avatar soft">{initials(p.nombre_completo)}</span><span><strong>{p.nombre_completo}</strong><small>{p.cuip?'CUIP':'CURP'} · {p.cuip||p.curp}</small></span></Link></td><td><strong className="cell-main">{p.corporacion}</strong><small>{p.adscripcion}</small>{p.estatus!=='activo'&&<small className="muted">Situación: {p.estatus}</small>}</td><td><Badge value={p.estatus_vigencia}/></td><td><strong className="cell-main">{formatDate(p.fecha_vencimiento)}</strong><small>{p.dias_restantes===null?'Sin vigencia acreditada':p.dias_restantes<0?`Venció hace ${-p.dias_restantes} días`:p.dias_restantes===0?'Vence hoy':`Faltan ${p.dias_restantes} días`}</small></td><td><Link className="row-action" aria-label={`Abrir expediente de ${p.nombre_completo}`} to={`/personal/${p.personal_id}`}><ArrowRight size={19}/></Link></td></tr>)}</tbody></table></div><div className="pagination"><span>Registros {offset+1}–{offset+rows.data.items.length}</span><div><button className="icon-button" aria-label="Página anterior" disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-25))}><ChevronLeft size={19}/></button><span>Página {offset/25+1}</span><button className="icon-button" aria-label="Página siguiente" disabled={!rows.data.has_more} onClick={()=>setOffset(offset+25)}><ChevronRight size={19}/></button></div></div></>:!rows.error&&<div className="empty"><Search size={30}/><h3>No hay elementos para mostrar</h3><p>{q||vig||corp?'Prueba con otros filtros o términos de búsqueda.':'Registra un elemento para comenzar el seguimiento.'}</p>{user.rol==='admin'&&!q&&!vig&&!corp&&<Link className="button secondary" to="/personal/nuevo">Registrar elemento</Link>}</div>}
  </section><p className="footnote">La vigencia se calcula a la fecha de consulta. Las tarjetas consideran únicamente al personal activo.</p></>;
}

function Detail(){
 const {id}=useParams(),user=useUser(),[showForm,setShowForm]=useState(false),[success,setSuccess]=useState('');
 const person=useData<Person>(`/personal/${id}`),history=useData<Evaluation[]>(`/competencias-basicas/${id}`);
 if(person.loading)return <Loading/>;
 if(person.error)return <ErrorBox message={person.error}/>;
 const p=person.data!;
 return <>{user.rol!=='trabajador'&&<Link className="back-link" to="/estado-fuerza"><ArrowLeft size={17}/>Volver al estado de fuerza</Link>}<div className="page-heading"><div><span className="eyebrow">EXPEDIENTE DEL ELEMENTO</span><h1>{p.nombre_completo}</h1><p>{p.cuip?'CUIP':'CURP'} · {p.cuip||p.curp}</p></div>{user.rol==='admin'&&<Link className="button secondary" to={`/personal/${id}/editar`}>Editar datos</Link>}</div>
  {success&&<div className="success" role="status"><Check size={18}/>{success}</div>}
  <div className="detail-grid"><section className="surface"><h2>Datos del personal</h2><dl className="facts">{[['Corporación',p.corporacion],['Adscripción',p.adscripcion],['CUIP',p.cuip],['CURP',p.curp],['Cargo',p.cargo],['Grado',p.grado],['Sexo',p.sexo==='H'?'Hombre':p.sexo==='M'?'Mujer':null],['Situación',p.estatus]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value||'Sin registrar'}</dd></div>)}</dl></section><section className="surface vigencia-card"><span className="eyebrow">COMPETENCIAS BÁSICAS</span><Badge value={p.estatus_vigencia}/><h2>{p.fecha_vencimiento?formatDate(p.fecha_vencimiento):'Sin vigencia acreditada'}</h2><p>{p.fecha_vencimiento?'Fecha de vencimiento de la evaluación actual.':'Registra una evaluación aprobada para acreditar la vigencia.'}</p><dl><dt>Certificación</dt><dd>{formatDate(p.fecha_certificacion)}</dd></dl>{user.rol!=='trabajador'&&<button className="button primary wide" onClick={()=>setShowForm(!showForm)}><Plus size={18}/>{showForm?'Cerrar captura':'Registrar evaluación'}</button>}</section></div>
  {showForm&&<CompetenciaForm personId={id!} onCancel={()=>setShowForm(false)} onSaved={()=>{setShowForm(false);setSuccess('Evaluación registrada. El historial y la vigencia se actualizaron.');person.reload();history.reload();}}/>}
  <div className="action-row phase-form"><Link className="button secondary" to={`/personal/${id}/bitacora`}><FileText size={18}/>Consultar bitácora y cursos</Link></div>
  <section className="table-panel history"><div className="panel-heading"><h2>Historial de evaluaciones</h2><span className="muted">{history.data?.length??0} registros</span></div><ErrorBox message={history.error}/>{history.loading?<Loading/>:history.data?.length?<div className="table-scroll"><table><thead><tr><th>Fecha de certificación</th><th>Institución evaluadora</th><th>Folio</th><th>Resultado</th><th>Registro</th></tr></thead><tbody>{history.data.map(e=><tr key={e.id}><td>{formatDate(e.fecha_certificacion)}</td><td>{e.institucion_evaluadora}</td><td>{e.folio}</td><td><Badge value={e.resultado==='aprobado'?'Aprobado':'No aprobado'}/></td><td>{e.activo?'Actual':'Histórico'}</td></tr>)}</tbody></table></div>:<div className="empty"><ClipboardCheck size={30}/><h3>Aún no hay evaluaciones</h3><p>El historial aparecerá después de registrar la primera evaluación.</p></div>}</section></>;
}

function EditPerson(){const {id}=useParams();const result=useData<Person>(`/personal/${id}`);return result.loading?<Loading/>:result.error?<ErrorBox message={result.error}/>:<PersonForm existing={result.data!}/>;}

function PersonForm({existing}:{existing?:Person}){
 const catalogs=useData<Catalogs>('/catalogos'),navigate=useNavigate(),[busy,setBusy]=useState(false),[error,setError]=useState('');
 async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();const d=Object.fromEntries(new FormData(e.currentTarget));for(const k of ['cuip','curp','sexo','cargo_id','grado_id'])if(!d[k])d[k]=null as unknown as string;
  setBusy(true);setError('');try{const p=await api<{id:string}>(existing?`/personal/${existing.personal_id}`:'/personal',{method:existing?'PUT':'POST',body:JSON.stringify(d)});navigate(`/personal/${p.id}`);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 if(catalogs.loading)return <Loading/>;
 const empty=!catalogs.data?.corporaciones.some(c=>c.activo);
 return <><Link className="back-link" to={existing?`/personal/${existing.personal_id}`:'/estado-fuerza'}><ArrowLeft size={17}/>Volver</Link><div className="page-heading"><div><span className="eyebrow">ESTADO DE FUERZA</span><h1>{existing?'Editar expediente':'Registrar elemento'}</h1><p>Captura el CUIP o, si aún no está disponible, la CURP.</p></div></div><ErrorBox message={catalogs.error}/>{empty&&<ErrorBox message="Es necesario registrar al menos una corporación en el catálogo de Supabase antes de dar de alta personal."/>}<form className="surface record-form" onSubmit={submit}><h2>Identificación del elemento</h2><div className="form-grid"><label className="span-two">Nombre completo *<input name="nombre_completo" defaultValue={existing?.nombre_completo} minLength={3} maxLength={150} required/></label><label>CUIP<input name="cuip" defaultValue={existing?.cuip??''} maxLength={20} className="uppercase"/><small>Identificador preferente; hasta 20 caracteres.</small></label><label>CURP<input name="curp" defaultValue={existing?.curp??''} minLength={18} maxLength={18} className="uppercase"/><small>Obligatoria cuando no se cuenta con CUIP.</small></label><label>Sexo<select name="sexo" defaultValue={existing?.sexo??''}><option value="">Sin registrar</option><option value="H">Hombre</option><option value="M">Mujer</option></select></label><label>Situación del personal<select name="estatus" defaultValue={existing?.estatus??'activo'}>{['activo','baja','comisionado','licencia'].map(s=><option key={s} value={s}>{s[0].toUpperCase()+s.slice(1)}</option>)}</select></label></div><h2 className="form-section">Adscripción</h2><div className="form-grid"><label>Corporación *<select name="corporacion_id" defaultValue={existing?.corporacion_id??''} required><option value="">Seleccionar corporación</option>{catalogs.data?.corporaciones.filter(c=>c.activo||c.id===existing?.corporacion_id).map(c=><option key={c.id} value={c.id}>{c.nombre}</option>)}</select></label><label>Área o unidad *<input name="adscripcion" defaultValue={existing?.adscripcion} required maxLength={150}/></label>{(['cargos','grados'] as const).map((key,i)=><label key={key}>{i===0?'Cargo':'Grado'}<select name={i===0?'cargo_id':'grado_id'} defaultValue={(i===0?existing?.cargo_id:existing?.grado_id)??''}><option value="">Sin registrar</option>{catalogs.data?.[key].filter(c=>c.activo||c.id===(i===0?existing?.cargo_id:existing?.grado_id)).map(c=><option key={c.id} value={c.id}>{c.nombre}</option>)}</select></label>)}</div><ErrorBox message={error}/><div className="form-actions"><span className="muted">* Campos obligatorios</span><Link className="button secondary" to={existing?`/personal/${existing.personal_id}`:'/estado-fuerza'}>Cancelar</Link><button className="button primary" disabled={busy||empty}>{busy?'Guardando…':'Guardar expediente'}</button></div></form></>;
}

function CompetenciaForm({personId,onCancel,onSaved}:{personId:string;onCancel:()=>void;onSaved:()=>void}){
 const [error,setError]=useState(''),[busy,setBusy]=useState(false);
 async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();const data={...Object.fromEntries(new FormData(e.currentTarget)),personal_id:personId};setBusy(true);setError('');try{await api('/competencias-basicas',{method:'POST',body:JSON.stringify(data)});onSaved();}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 return <form className="surface record-form evaluation-form" onSubmit={submit}><h2>Registrar evaluación de competencias básicas</h2><p className="muted">La evaluación más reciente determina el estado actual. Un resultado no aprobado no acredita vigencia. Una evaluación anterior se conserva como histórico.</p><div className="form-grid"><label>Institución evaluadora *<input name="institucion_evaluadora" required minLength={2} maxLength={150}/></label><label>Folio *<input name="folio" required maxLength={60}/></label><label>Fecha de certificación / evaluación *<input name="fecha_certificacion" type="date" required max={today()}/></label><label>Resultado *<select name="resultado" required defaultValue=""><option value="" disabled>Seleccionar resultado</option><option value="aprobado">Aprobado</option><option value="no_aprobado">No aprobado</option></select></label></div><p className="footnote">Los resultados aprobados tienen vigencia de tres años. Si hay dos evaluaciones con la misma fecha, la última capturada será la actual.</p><ErrorBox message={error}/><div className="form-actions"><button type="button" className="button secondary" onClick={onCancel}>Cancelar</button><button className="button primary" disabled={busy}>{busy?'Guardando…':'Guardar evaluación'}</button></div></form>;
}
