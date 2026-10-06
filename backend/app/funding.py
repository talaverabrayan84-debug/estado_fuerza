"""Institutional course journal. The supplied workbook owns the table layout."""
import json
import math
import re
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr
from app.core.security import Context, allow, context
from app.services.vigencia import hoy_local

LAYOUTS = json.loads((Path(__file__).parent/'assets/funding_layout.json').read_text(encoding='utf-8'))
router = APIRouter(prefix='/api/bitacora-fondos', tags=['Bitácora FASP y FOFISP'])

class Change(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: int = Field(ge=1)
    section: Literal['values','receipts'] = 'values'
    key: str = Field(min_length=2,max_length=20)
    value: StrictStr | StrictInt | StrictFloat | None = None

def cells(layout):
    return {c['key']:c for row in layout['rows'][layout['header']:] for c in row}

def delivery_cells(layout):
    return [c for c in cells(layout).values() if c['col']==layout['due_col']]

def groups(layout, data, today=None):
    today = today or hoy_local()
    values, receipts = data['values'], data['receipts']
    result = []
    for c in delivery_cells(layout):
        start, end = c['row'], c['row']+c['span'][0]
        names = [str(values[x['key']]) for row in layout['rows'][start-1:end-1] for x in row
                 if x['col']=='B' and values.get(x['key'])]
        raw = values.get(c['key'])
        received = receipts.get(c['key'])
        # A check in the UMS deliverables column is explicit receipt in the source.
        marked = str(raw or '').strip().upper()=='ENTREGADO' or str(values.get('O'+str(start)) or '').strip() in ('✔','✓')
        try: due = date.fromisoformat(str(raw))
        except ValueError: due = None
        days = (due-today).days if due else None
        status = 'recibida' if received or marked else 'sin_fecha' if due is None else 'vencida' if days<0 else 'hoy' if days==0 else '1_dia' if days<=1 else '3_dias' if days<=3 else '7_dias' if days<=7 else 'programada'
        result.append({'key':c['key'],'fund':layout['name'],'course':' / '.join(names) or f'Curso en fila {start}',
                       'due':due.isoformat() if due else None,'days':days,'status':status,'received':received,
                       'source_received':marked})
    return result

def demo_documents(store):
    if not hasattr(store,'funding'):
        # Never mix the user's real workbook data with a fictitious demo.
        store.funding = {}
        for fund, layout in LAYOUTS.items():
            values = {k:None for k in cells(layout)}
            first = delivery_cells(layout)[0]
            values['B'+str(first['row'])] = 'Curso de demostración '+fund
            values[first['key']] = (hoy_local()+timedelta(days=7)).isoformat()
            store.funding[fund] = {'fund':fund,'version':1,'data':{'values':values,'receipts':{}}}
    return store.funding

def documents(ctx):
    if hasattr(ctx.repo,'store'):
        with ctx.repo.store.lock: return deepcopy(list(demo_documents(ctx.repo.store).values()))
    rows = ctx.repo.request('GET','/rest/v1/bitacora_fondos',params={'select':'fund,version,data','order':'fund'})
    if len(rows)!=2: raise HTTPException(503,'La bitácora requiere instalar la migración 004 y cargar el archivo de referencia.')
    return rows

def validate_change(layout, change):
    editable = cells(layout)
    c = editable.get(change.key)
    if not c: raise HTTPException(422,'Esta celda no es editable.')
    v = change.value
    if isinstance(v,str) and len(v)>5000: raise HTTPException(422,'El contenido no puede superar 5,000 caracteres.')
    if isinstance(v,float) and not math.isfinite(v): raise HTTPException(422,'Ingrese un número finito.')
    if change.section=='receipts':
        if c['col']!=layout['due_col']: raise HTTPException(422,'Seleccione una entrega UMS.')
        if v is None: return
        try:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',str(v)): raise ValueError()
            receipt = date.fromisoformat(str(v))
        except ValueError: raise HTTPException(422,'Ingrese la fecha de recepción completa.')
        if receipt>hoy_local(): raise HTTPException(422,'La recepción no puede ser futura.')
    elif c['kind']=='date' and v is not None:
        if str(v).strip().upper() in ('N/A','ENTREGADO'): return
        try:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',str(v)): raise ValueError()
            date.fromisoformat(str(v))
        except ValueError: raise HTTPException(422,'Use una fecha válida, N/A o ENTREGADO.')

@router.get('')
def journal(ctx:Context=Depends(context)):
    allow(ctx,'admin','capacitacion')
    return {'sheets':[{**r,'layout':LAYOUTS[r['fund']],'deliveries':groups(LAYOUTS[r['fund']],r['data'])} for r in documents(ctx)]}

@router.get('/alertas')
def alerts(ctx:Context=Depends(context)):
    allow(ctx,'admin','capacitacion')
    all_groups = [g for r in documents(ctx) for g in groups(LAYOUTS[r['fund']],r['data'])]
    active = [g for g in all_groups if g['status'] in ('vencida','hoy','1_dia','3_dias','7_dias')]
    return {'items':sorted(active,key=lambda g:(g['due'],g['fund'],g['key'])),
            'missing_dates':sum(g['status']=='sin_fecha' for g in all_groups),'as_of':hoy_local().isoformat()}

@router.put('/{fund}')
def change_cell(fund:Literal['FASP','FOFISP'],change:Change,ctx:Context=Depends(context)):
    allow(ctx,'admin','capacitacion')
    validate_change(LAYOUTS[fund],change)
    if hasattr(ctx.repo,'store'):
        with ctx.repo.store.lock:
            doc = demo_documents(ctx.repo.store)[fund]
            if doc['version']!=change.version: raise HTTPException(409,'La bitácora cambió. Actualice antes de guardar.')
            doc['data'][change.section][change.key] = change.value
            doc['version'] += 1
            return deepcopy(doc)
    return ctx.repo.request('POST','/rest/v1/rpc/actualizar_bitacora_fondo',json={
        'fondo':fund,'revision':change.version,'seccion':change.section,'celda':change.key,'valor':change.value})
