from datetime import date, timedelta
import pytest
from app.services.vigencia import calcular_vencimiento, evaluar_vigencia, hoy_local
from app.core.config import Settings
from app.db.demo import CORP_A, WORKER_ID

@pytest.mark.parametrize('days,expected',[(-1,'Vencida'),(0,'Por vencer'),(1,'Por vencer'),(90,'Por vencer'),(91,'Vigente')])
def test_boundaries(days,expected):
    today=date(2026,9,10)
    assert evaluar_vigencia(today+timedelta(days=days),today)==expected

def test_leap_year():
    assert calcular_vencimiento(date(2024,2,29))==date(2027,2,28)

def test_configurable_threshold():
    assert evaluar_vigencia(date(2026,11,9),date(2026,9,10),60)=='Por vencer'

def personal(**extra):
    return {'cuip':'PRUEBA001','nombre_completo':'Persona de prueba','corporacion_id':CORP_A,'adscripcion':'Área de prueba',**extra}

def evaluation(**extra):
    return {'personal_id':WORKER_ID,'institucion_evaluadora':'Institución prueba','fecha_certificacion':'2024-02-29','resultado':'aprobado','folio':'NUEVO',**extra}

def test_auth_required(client):
    assert client.get('/api/personal').status_code==401
    assert client.get('/api/personal',headers={'Authorization':'Bearer falsificado'}).status_code==401

def test_personal_create_normalize_unique_and_update(client,auth):
    h=auth()
    r=client.post('/api/personal',headers=h,json=personal(cuip=' prueba001 '))
    assert r.status_code==201 and r.json()['cuip']=='PRUEBA001'
    pid=r.json()['id']
    assert client.post('/api/personal',headers=h,json=personal()).status_code==409
    assert client.put(f'/api/personal/{pid}',headers=h,json=personal(estatus='baja')).status_code==200
    assert client.get(f'/api/personal/{pid}',headers=h).json()['estatus']=='baja'

def test_curp_fallback_and_required_identifier(client,auth):
    h=auth()
    assert client.post('/api/personal',headers=h,json=personal(cuip=None)).status_code==422
    assert client.post('/api/personal',headers=h,json=personal(cuip=None,curp='INVALIDO')).status_code==422
    assert client.post('/api/personal',headers=h,json=personal(cuip=None,curp='ABCD900101HMCLRS09')).status_code==201

def test_catalog_and_extra_fields_validation(client,auth):
    h=auth()
    assert client.post('/api/personal',headers=h,json=personal(corporacion_id='00000000-0000-0000-0000-000000000000')).status_code==422
    assert client.post('/api/personal',headers=h,json=personal(rol='admin')).status_code==422

def test_worker_isolation(client,auth):
    h=auth('trabajador')
    assert client.get('/api/personal',headers=h).status_code==403
    assert client.get('/api/alertas/resumen',headers=h).status_code==403
    assert client.get(f'/api/personal/{WORKER_ID}',headers=h).status_code==200
    assert client.get('/api/personal/00000000-0000-0000-0000-000000000000',headers=h).status_code==404
    assert client.post('/api/personal',headers=h,json=personal()).status_code==403
    assert client.post('/api/competencias-basicas',headers=h,json=evaluation()).status_code==403

def test_capacitacion_permissions(client,auth):
    h=auth('capacitacion')
    assert client.get('/api/personal',headers=h).status_code==200
    assert client.post('/api/personal',headers=h,json=personal()).status_code==403
    assert client.put(f'/api/personal/{WORKER_ID}',headers=h,json=personal()).status_code==403
    assert client.post('/api/competencias-basicas',headers=h,json=evaluation()).status_code==201

def test_evaluations_history_duplicates_and_failed_result(client,auth):
    h=auth()
    r=client.post('/api/competencias-basicas',headers=h,json=evaluation())
    assert r.status_code==201 and r.json()['fecha_vencimiento']=='2027-02-28'
    assert client.post('/api/competencias-basicas',headers=h,json=evaluation()).status_code==409
    old=client.post('/api/competencias-basicas',headers=h,json=evaluation(fecha_certificacion='2020-01-01',folio='HISTORICO')).json()
    assert old['activo'] is False
    failed=client.post('/api/competencias-basicas',headers=h,json=evaluation(fecha_certificacion=hoy_local().isoformat(),resultado='no_aprobado',folio='NOAPROBADO')).json()
    assert failed['activo'] and failed['fecha_vencimiento'] is None
    current=client.get(f'/api/personal/{WORKER_ID}',headers=h).json()
    assert current['estatus_vigencia']=='No aprobado'
    history=client.get(f'/api/competencias-basicas/{WORKER_ID}',headers=h).json()
    assert sum(e['activo'] for e in history)==1

def test_future_date_rejected(client,auth):
    assert client.post('/api/competencias-basicas',headers=auth(),json=evaluation(fecha_certificacion=(hoy_local()+timedelta(days=1)).isoformat())).status_code==422

def test_pagination_search_and_alerts(client,auth):
    h=auth()
    page=client.get('/api/personal?limit=2',headers=h).json()
    assert len(page['items'])==2 and page['has_more']
    assert len(client.get('/api/personal?q=DEMO00001',headers=h).json()['items'])==1
    assert client.get('/api/personal?limit=0',headers=h).status_code==422
    summary=client.get('/api/alertas/resumen',headers=h).json()
    assert summary['total']==sum(summary[s] for s in ['Vigente','Por vencer','Vencida','Sin registro','No aprobado'])
    assert summary['Sin registro']==1

def test_logout_invalidates_demo_session(client,auth):
    h=auth()
    assert client.delete('/api/demo/session',headers=h).status_code==204
    assert client.get('/api/me',headers=h).status_code==401

def test_demo_forbidden_in_production():
    with pytest.raises(RuntimeError): Settings(environment='production',demo=True).validate()

def test_real_backend_forwards_user_jwt(monkeypatch):
    from app.db.supabase_client import SupabaseRepository
    import httpx
    seen=[]
    def request(method,url,**kwargs):
        seen.append(kwargs['headers'])
        data={'id':'authenticated-user','email':'test@example.invalid'} if '/auth/v1/user' in url else [{'id':'authenticated-user','rol':'trabajador','activo':True,'personal_id':WORKER_ID}]
        return httpx.Response(200,json=data)
    monkeypatch.setattr(httpx,'request',request)
    repo=SupabaseRepository('signed-user-token')
    assert repo.profile()['rol']=='trabajador'
    assert all(h['Authorization']=='Bearer signed-user-token' for h in seen)

def test_disabled_profile_rejected(monkeypatch):
    from app.db.supabase_client import SupabaseRepository
    from fastapi import HTTPException
    import httpx
    def request(method,url,**kwargs):
        return httpx.Response(200,json={'id':'disabled'} if '/auth/v1/user' in url else [{'id':'disabled','rol':'admin','activo':False}])
    monkeypatch.setattr(httpx,'request',request)
    with pytest.raises(HTTPException) as error: SupabaseRepository('token').profile()
    assert error.value.status_code==403
