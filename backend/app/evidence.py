from copy import deepcopy
from uuid import UUID, uuid4
from pathlib import PurePath
import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from app.core.config import settings
from app.core.security import Context, context, allow

router=APIRouter(prefix='/api/bitacora')
BUCKET='bitacora-evidencias'
MAX_SIZE=2*1024*1024

def evidence(ctx,entry_id):
    ctx.repo.journal_entry(entry_id)
    if settings.demo:
        row=ctx.repo.store.evidence.get(entry_id)
        return [{k:v for k,v in row.items() if k!='content'}] if row else []
    return ctx.repo.request('GET','/rest/v1/bitacora_evidencias',params={'bitacora_id':f'eq.{entry_id}','select':'*'})

def storage(ctx,method,path,**kwargs):
    try:
        r=httpx.request(method,settings.supabase_url+'/storage/v1'+path,headers={**ctx.repo.headers,**kwargs.pop('headers',{})},timeout=20,**kwargs)
    except httpx.RequestError: raise HTTPException(503,'No fue posible conectar con el almacenamiento.')
    if r.is_error: raise HTTPException(502,'No se pudo acceder a la evidencia. Verifique la configuración de Storage y vuelva a intentar.')
    return r

@router.get('/{entry_id}/evidencia')
def info(entry_id:UUID,ctx:Context=Depends(context)):
    rows=evidence(ctx,str(entry_id))
    return rows[0] if rows else None

@router.post('/{entry_id}/evidencia',status_code=201)
def upload(entry_id:UUID,archivo:UploadFile=File(...),ctx:Context=Depends(context)):
    allow(ctx,'trabajador')
    eid=str(entry_id);entry=ctx.repo.journal_entry(eid)
    if entry['personal_id']!=ctx.user['personal_id'] or entry['creado_por']!=ctx.user['id']: raise HTTPException(403,'Sin permiso para adjuntar evidencia.')
    if evidence(ctx,eid): raise HTTPException(409,'La actividad ya tiene una evidencia adjunta.')
    content=archivo.file.read(MAX_SIZE+1)
    if not content or len(content)>MAX_SIZE: raise HTTPException(413,'La evidencia debe pesar entre 1 byte y 2 MB.')
    name=PurePath((archivo.filename or '').replace('\\','/')).name[:200]
    ext=PurePath(name).suffix.lower()
    if ext=='.pdf' and content.startswith(b'%PDF-'): mime='application/pdf';ext='pdf'
    elif ext=='.png' and content.startswith(b'\x89PNG\r\n\x1a\n'): mime='image/png';ext='png'
    elif ext in ('.jpg','.jpeg') and content.startswith(b'\xff\xd8\xff'): mime='image/jpeg';ext='jpg'
    else: raise HTTPException(422,'Adjunte un archivo PDF, PNG o JPG válido.')
    path=f"{entry['personal_id']}/{eid}/{uuid4()}.{ext}"
    row={'ruta':path,'nombre':name,'tipo':mime,'tamano':len(content)}
    if settings.demo:
        with ctx.repo.store.lock:
            if eid in ctx.repo.store.evidence: raise HTTPException(409,'La actividad ya tiene evidencia.')
            ctx.repo.store.evidence[eid]={**row,'id':str(uuid4()),'bitacora_id':eid,'content':content}
        return {**row,'bitacora_id':eid}
    storage(ctx,'POST',f'/object/{BUCKET}/{path}',content=content,headers={'Content-Type':mime,'x-upsert':'false'})
    try:
        return ctx.repo.request('POST','/rest/v1/rpc/vincular_evidencia',json={'entrada':eid,'datos':row})
    except HTTPException:
        # A response can be lost after a successful commit. Inspect before cleanup.
        try:
            current=evidence(ctx,eid)
            if current and current[0]['ruta']==path: return current[0]
            storage(ctx,'DELETE',f'/object/{BUCKET}',json={'prefixes':[path]})
        except HTTPException: pass
        raise

@router.get('/{entry_id}/evidencia/descargar')
def download(entry_id:UUID,ctx:Context=Depends(context)):
    eid=str(entry_id);rows=evidence(ctx,eid)
    if not rows: raise HTTPException(404,'La actividad no tiene evidencia.')
    row=rows[0]
    if settings.demo: content=deepcopy(ctx.repo.store.evidence[eid]['content'])
    else: content=storage(ctx,'GET',f"/object/authenticated/{BUCKET}/{row['ruta']}").content
    ext={'application/pdf':'pdf','image/png':'png','image/jpeg':'jpg'}[row['tipo']]
    return Response(content,media_type=row['tipo'],headers={'Content-Disposition':f'attachment; filename="evidencia.{ext}"'})
