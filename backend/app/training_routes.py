import csv
from io import BytesIO, StringIO
from pathlib import PurePath
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from app.core.security import Context, allow, context, own_or_staff
from app.training_schemas import CursoIn, SesionIn, InscripcionIn, BitacoraIn
from app.services.imports import MAX_BYTES, HEADERS, read_file, build_preview, template, target_valid
from app.services.uploads import upload_filename
from app.services.calendar_dates import CalendarDate

router=APIRouter(prefix='/api')

def page(rows, offset, limit):
    return {'items':rows[:limit],'has_more':len(rows)>limit,'offset':offset,'limit':limit}

@router.get('/cursos')
def courses(offset:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=100),ctx:Context=Depends(context)):
    return page(ctx.repo.courses(offset,limit+1),offset,limit)

@router.post('/cursos',status_code=201)
def add_course(data:CursoIn,ctx:Context=Depends(context)):
    allow(ctx,'admin','capacitacion')
    return ctx.repo.save_course(data.model_dump(mode='json'))

@router.put('/cursos/{course_id}')
def update_course(course_id:UUID,data:CursoIn,ctx:Context=Depends(context)):
    allow(ctx,'admin','capacitacion')
    return ctx.repo.save_course(data.model_dump(mode='json'),str(course_id))

@router.get('/curso-sesiones')
def sessions(desde:CalendarDate,hasta:CalendarDate,offset:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=500),ctx:Context=Depends(context)):
    if hasta<desde or (hasta-desde).days>366: raise HTTPException(422,'Consulte un rango de hasta un año, con término posterior al inicio.')
    return page(ctx.repo.sessions(desde.isoformat(),hasta.isoformat(),offset,limit+1),offset,limit)

@router.get('/curso-sesiones/{session_id}')
def session(session_id:UUID,ctx:Context=Depends(context)):
    return ctx.repo.session(str(session_id))

@router.post('/curso-sesiones',status_code=201)
def add_session(data:SesionIn,ctx:Context=Depends(context)):
    allow(ctx,'admin','capacitacion')
    return ctx.repo.save_session(data.model_dump(mode='json'))

@router.put('/curso-sesiones/{session_id}')
def update_session(session_id:UUID,data:SesionIn,ctx:Context=Depends(context)):
    allow(ctx,'admin','capacitacion')
    return ctx.repo.save_session(data.model_dump(mode='json'),str(session_id))

@router.get('/curso-sesiones/{session_id}/inscripciones')
def session_enrollments(session_id:UUID,offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),ctx:Context=Depends(context)):
    ctx.repo.session(str(session_id))
    return page(ctx.repo.enrollments(session_id=str(session_id),offset=offset,limit=limit+1),offset,limit)

@router.post('/curso-sesiones/{session_id}/inscripciones')
def enroll(session_id:UUID,data:InscripcionIn,ctx:Context=Depends(context)):
    allow(ctx,'admin','capacitacion')
    return ctx.repo.enroll(str(session_id),data.model_dump(mode='json'))

@router.get('/personal/{person_id}/inscripciones')
def person_enrollments(person_id:UUID,offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),ctx:Context=Depends(context)):
    own_or_staff(ctx,person_id)
    ctx.repo.get_personal(str(person_id))
    return page(ctx.repo.enrollments(person_id=str(person_id),offset=offset,limit=limit+1),offset,limit)

@router.get('/personal/{person_id}/bitacora')
def journal(person_id:UUID,offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),ctx:Context=Depends(context)):
    own_or_staff(ctx,person_id)
    ctx.repo.get_personal(str(person_id))
    return page(ctx.repo.journal(str(person_id),offset,limit+1),offset,limit)

@router.post('/bitacora',status_code=201)
def add_journal(data:BitacoraIn,ctx:Context=Depends(context)):
    allow(ctx,'trabajador')
    return ctx.repo.save_journal(data.model_dump(mode='json'))

@router.put('/bitacora/{entry_id}')
def update_journal(entry_id:UUID,data:BitacoraIn,ctx:Context=Depends(context)):
    allow(ctx,'trabajador')
    ctx.repo.journal_entry(str(entry_id))
    return ctx.repo.save_journal(data.model_dump(mode='json'),str(entry_id))

@router.get('/carga-masiva/plantilla')
def import_template(destino:str,formato:str='csv',ctx:Context=Depends(context)):
    allow(ctx,'admin'); target_valid(destino)
    if formato=='csv': content=template(destino); media='text/csv'
    elif formato=='xlsx':
        from openpyxl import Workbook
        book=Workbook(); book.active.append(HEADERS[destino])
        book.active.freeze_panes='A2'
        for column in book.active.columns: book.active.column_dimensions[column[0].column_letter].width=28
        out=BytesIO(); book.save(out); book.close(); content=out.getvalue()
        media='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    else: raise HTTPException(422,'Formato no admitido.')
    return Response(content,media_type=media,headers={'Content-Disposition':f'attachment; filename="plantilla-{destino}.{formato}"'})

@router.post('/carga-masiva/previsualizar',status_code=201)
def preview(destino:str=Form(...),archivo:UploadFile=File(...),ctx:Context=Depends(context)):
    allow(ctx,'admin'); target_valid(destino)
    name=upload_filename(archivo.filename)
    content=archivo.file.read(MAX_BYTES+1)
    rows=read_file(content,name,destino)
    return ctx.repo.stage_import({'nombre_archivo':name,'tipo_archivo':PurePath(name).suffix[1:].lower(),
        'tabla_destino':destino,'filas':build_preview(rows,destino,ctx.repo)})

@router.get('/carga-masiva')
def imports(offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),ctx:Context=Depends(context)):
    allow(ctx,'admin')
    return page(ctx.repo.imports(offset,limit+1),offset,limit)

@router.get('/carga-masiva/{import_id}')
def import_detail(import_id:UUID,ctx:Context=Depends(context)):
    allow(ctx,'admin')
    return ctx.repo.import_detail(str(import_id))

@router.post('/carga-masiva/{import_id}/confirmar')
def confirm_import(import_id:UUID,ctx:Context=Depends(context)):
    allow(ctx,'admin')
    return ctx.repo.confirm_import(str(import_id))

@router.get('/carga-masiva/{import_id}/reporte')
def report(import_id:UUID,ctx:Context=Depends(context)):
    allow(ctx,'admin')
    record=ctx.repo.import_detail(str(import_id))
    out=StringIO(); writer=csv.writer(out)
    writer.writerow(['fila','identificador','accion','resultado','errores'])
    def safe(v):
        s=str(v)
        return "'"+s if s.lstrip().startswith(('=','+','-','@','\t','\r')) else s
    for r in record['filas']:
        writer.writerow([r['fila'],safe(r['identificador']),r['accion'],
            'error' if r['errores'] else 'procesado' if record['estado']=='confirmada' else 'validado',safe(' | '.join(r['errores']))])
    return Response(out.getvalue().encode('utf-8-sig'),media_type='text/csv',
        headers={'Content-Disposition':'attachment; filename="reporte-carga.csv"'})
