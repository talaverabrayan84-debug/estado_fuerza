import httpx
from fastapi import HTTPException
from app.core.config import settings
from app.db.training import TrainingRepository

class SupabaseRepository(TrainingRepository):
    """Every request carries the caller JWT; never a service_role key."""
    def __init__(self, token: str):
        self.headers = {'apikey': settings.supabase_key, 'Authorization': f'Bearer {token}'}

    def request(self, method, path, *, params=None, json=None):
        try:
            r = httpx.request(method, settings.supabase_url + path, headers={**self.headers, 'Prefer': 'return=representation'},
                              params=params, json=json, timeout=15)
        except httpx.RequestError:
            raise HTTPException(503, 'No fue posible conectar con la base de datos.')
        if r.is_error:
            try:
                code = r.json().get('code')
            except ValueError:
                code = None
            if code == '23505':
                raise HTTPException(409, 'Ya existe el identificador o la evaluación registrada.')
            if code == 'P0001':
                raise HTTPException(409, r.json().get('message', 'Los datos cambiaron. Repita la operación.'))
            if code in ('23503', '23514', '22023'):
                raise HTTPException(422, 'Verifique los datos, catálogos y fechas del registro.')
            if r.status_code in (401, 403) or code == '42501':
                raise HTTPException(403, 'La sesión no tiene permiso para esta operación.')
            raise HTTPException(502, 'No se pudo completar la operación en Supabase.')
        return r.json() if r.content else None

    def profile(self):
        user = self.request('GET', '/auth/v1/user')
        rows = self.request('GET', '/rest/v1/usuarios', params={'id': f'eq.{user["id"]}', 'select': '*'})
        if not rows or not rows[0]['activo']:
            raise HTTPException(403, 'Cuenta sin acceso habilitado. Contacte a su administrador.')
        return {**rows[0], 'email': user.get('email', '')}

    def catalogs(self):
        return {name: self.request('GET', f'/rest/v1/{name}', params={'select': '*', 'order': 'nombre'})
                for name in ('corporaciones', 'cargos', 'grados')}

    def list_personal(self, *, q='', estatus='', corporacion_id='', vigencia='', offset=0, limit=25):
        params = {'select': '*', 'order': 'nombre_completo,personal_id', 'offset': offset, 'limit': limit}
        if q:
            # Values are encoded by httpx; quotes escape PostgREST grammar, not SQL.
            clean = q.replace('\\', '\\\\').replace('"', '\\"').replace('%', '').replace('*', '')
            value = f'"*{clean}*"'
            params['or'] = f'(nombre_completo.ilike.{value},cuip.ilike.{value},curp.ilike.{value})'
        if estatus: params['estatus'] = f'eq.{estatus}'
        if corporacion_id: params['corporacion_id'] = f'eq.{corporacion_id}'
        if vigencia: params['estatus_vigencia'] = f'eq.{vigencia}'
        return self.request('GET', '/rest/v1/vw_vigencia_competencias', params=params)

    def get_personal(self, person_id):
        rows = self.request('GET', '/rest/v1/vw_vigencia_competencias', params={'personal_id': f'eq.{person_id}', 'select': '*'})
        if not rows: raise HTTPException(404, 'Expediente no encontrado.')
        return rows[0]

    def save_personal(self, data, person_id=None):
        path = '/rest/v1/personal'
        result = self.request('PATCH' if person_id else 'POST', path,
                              params={'id': f'eq.{person_id}'} if person_id else None, json=data)
        if not result: raise HTTPException(404, 'Expediente no encontrado.')
        return result[0]

    def history(self, person_id):
        rows = []
        offset = 0
        while True:
            page = self.request('GET', '/rest/v1/competencias_basicas', params={
                'personal_id': f'eq.{person_id}', 'select': '*',
                'order': 'fecha_certificacion.desc,activo.desc,created_at.desc,id.desc',
                'offset': offset, 'limit': 500})
            rows.extend(page)
            if len(page) < 500:
                return rows
            offset += 500

    def add_competencia(self, data):
        return self.request('POST', '/rest/v1/rpc/registrar_competencia', json={'datos': data})

    def summary(self):
        return self.request('POST', '/rest/v1/rpc/resumen_vigencia', json={})

    def config(self):
        rows = self.request('GET', '/rest/v1/configuracion', params={'id': 'eq.1', 'select': 'dias_alerta'})
        return rows[0]
