from datetime import date,timedelta
from app.funding import LAYOUTS,cells,delivery_cells,groups
from app.services.vigencia import hoy_local

def get_sheet(client,h,fund='FASP'):
    r=client.get('/api/bitacora-fondos',headers=h)
    assert r.status_code==200,r.text
    return next(s for s in r.json()['sheets'] if s['fund']==fund)

def change(client,h,s,key,value,section='values'):
    return client.put('/api/bitacora-fondos/'+s['fund'],headers=h,json={
        'version':s['version'],'section':section,'key':key,'value':value})

def test_template_and_permissions(client,auth):
    assert client.get('/api/bitacora-fondos').status_code==401
    worker=auth('trabajador')
    assert client.get('/api/bitacora-fondos',headers=worker).status_code==403
    assert client.get('/api/bitacora-fondos/alertas',headers=worker).status_code==403
    h=auth('capacitacion');s=get_sheet(client,h)
    assert s['layout']['due_col']=='J' and s['layout']['header']==2
    assert len(s['layout']['widths'])==20
    other=get_sheet(client,h,'FOFISP')
    assert other['layout']['due_col']=='I' and other['layout']['header']==7
    assert len(other['layout']['widths'])==19
    assert change(client,worker,s,'J3','2026-11-03').status_code==403
    # Changes persist, stale edits conflict, and template headings cannot change.
    r=change(client,h,s,'J3','2026-11-03');assert r.status_code==200,r.text
    assert get_sheet(client,h)['data']['values']['J3']=='2026-11-03'
    assert change(client,h,s,'B3','Cambio anterior').status_code==409
    fresh=get_sheet(client,h)
    assert change(client,h,fresh,'B2','Encabezado falso').status_code==422
    assert change(client,h,fresh,'J4','2026-11-03').status_code==422
    assert change(client,h,fresh,'J3','2026-02-30').status_code==422
    assert change(client,h,fresh,'J3','curso').status_code==422
    assert change(client,h,fresh,'B3',True).status_code==422
    assert get_sheet(client,h)['layout']==s['layout']

def test_alert_bands_grouping_and_receipt():
    layout=LAYOUTS['FASP'];values=dict.fromkeys(cells(layout));data={'values':values,'receipts':{}}
    now=date(2026,10,5)
    values['B3']='Curso';values['B6']='Evaluación'
    for days,status in [(8,'programada'),(7,'7_dias'),(4,'7_dias'),(3,'3_dias'),(2,'3_dias'),(1,'1_dia'),(0,'hoy'),(-1,'vencida')]:
        values['J3']=(now+timedelta(days=days)).isoformat()
        g=groups(layout,data,now)[0]
        assert g['status']==status and g['course']=='Curso / Evaluación'
        assert sum(x['key']=='J3' for x in groups(layout,data,now))==1
    values['O3']='Entrega parcial';assert groups(layout,data,now)[0]['status']=='vencida'
    values['O3']='✔';assert groups(layout,data,now)[0]['status']=='recibida'
    values['O3']=None;data['receipts']['J3']='2026-10-05';assert groups(layout,data,now)[0]['status']=='recibida'
    data['receipts']['J3']=None;values['J3']='ENTREGADO';assert groups(layout,data,now)[0]['status']=='recibida'
    values['J3']='N/A';assert groups(layout,data,now)[0]['status']=='sin_fecha'
    values['J3']=None;assert groups(layout,data,now)[0]['status']=='sin_fecha'

def test_live_alert_and_receipt_flow(client,auth):
    h=auth();s=get_sheet(client,h)
    assert change(client,h,s,'J3',(hoy_local()+timedelta(days=1)).isoformat()).status_code==200
    alerts=client.get('/api/bitacora-fondos/alertas',headers=h).json()
    assert any(d['fund']=='FASP' and d['key']=='J3' and d['status']=='1_dia' for d in alerts['items'])
    s=get_sheet(client,h)
    assert change(client,h,s,'J3',(hoy_local()+timedelta(days=1)).isoformat(),'receipts').status_code==422
    assert change(client,h,s,'B3',hoy_local().isoformat(),'receipts').status_code==422
    assert change(client,h,s,'J3',hoy_local().isoformat(),'receipts').status_code==200
    alerts=client.get('/api/bitacora-fondos/alertas',headers=h).json()
    assert not any(d['fund']=='FASP' and d['key']=='J3' for d in alerts['items'])
    assert change(client,h,get_sheet(client,h),'J3',None,'receipts').status_code==200
    assert any(d['fund']=='FASP' and d['key']=='J3' for d in client.get('/api/bitacora-fondos/alertas',headers=h).json()['items'])
