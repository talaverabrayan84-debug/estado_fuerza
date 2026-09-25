import {useState} from 'react';
import {Paperclip,Download} from 'lucide-react';
import {api,download} from '../api';
import {ErrorBox,useData} from '../components';
type EvidenceInfo={nombre:string;tipo:string;tamano:number};
export function Evidence({entryId,own}:{entryId:string;own:boolean}){
 const result=useData<EvidenceInfo|null>(`/bitacora/${entryId}/evidencia`),[file,setFile]=useState<File|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 function selectFile(candidate:File|null){setError('');setFile(null);if(candidate&&(!/\.(pdf|png|jpe?g)$/i.test(candidate.name)||candidate.size>2*1024*1024||!candidate.size)){setError('Selecciona un PDF, PNG o JPG no vacío, de hasta 2 MB.');return;}setFile(candidate);}
 async function upload(){if(!file||busy)return;setBusy(true);setError('');try{const d=new FormData();d.append('archivo',file);await api(`/bitacora/${entryId}/evidencia`,{method:'POST',body:d});result.reload();setFile(null);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 async function get(){if(!result.data||busy)return;setError('');setBusy(true);try{await download(`/bitacora/${entryId}/evidencia/descargar`,result.data.nombre);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 return <div className="evidence" aria-busy={busy||result.loading}><ErrorBox message={error||result.error}/>{result.error&&<button className="text-button" onClick={result.reload}>Reintentar consulta de evidencia</button>}{result.loading?<span className="muted">Consultando evidencia…</span>:result.data?<button className="text-button action-row" disabled={busy} onClick={get}><Download size={16}/>{busy?'Descargando…':result.data.nombre}<small>({Math.ceil(result.data.tamano/1024)} KB)</small></button>:!result.error&&own?<details><summary><Paperclip size={15}/> Adjuntar evidencia</summary><p className="footnote">Un archivo PDF, PNG o JPG de hasta 2 MB por actividad. Una vez adjunto se conserva con el registro.</p><label>Archivo de evidencia<input type="file" accept=".pdf,.png,.jpg,.jpeg" disabled={busy} onChange={e=>selectFile(e.target.files?.[0]??null)}/></label><button className="button secondary" disabled={busy||!file} onClick={upload}>{busy?'Adjuntando…':'Guardar evidencia'}</button></details>:null}</div>;
}
