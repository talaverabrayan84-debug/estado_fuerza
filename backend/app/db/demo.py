"""Datos ficticios en memoria: habilitación explícita, nunca para producción."""
from copy import deepcopy
from datetime import timedelta
from threading import RLock
from uuid import uuid4
from fastapi import HTTPException
from app.services.vigencia import hoy_local, detalle_vigencia

CORP_A = '10000000-0000-0000-0000-000000000001'
CORP_B = '10000000-0000-0000-0000-000000000002'
WORKER_ID = '20000000-0000-0000-0000-000000000001'

class DemoStore:
    def __init__(self):
        self.lock = RLock()
        self.people = {}
        self.evaluations = []
        self.catalogs = {
            'corporaciones': [{'id': CORP_A, 'nombre': 'Corporación de ejemplo A', 'activo': True},
                              {'id': CORP_B, 'nombre': 'Corporación de ejemplo B', 'activo': True}],
            'cargos': [], 'grados': []}
        names = ['Elemento de prueba 01', 'Elemento de prueba 02', 'Elemento de prueba 03',
                 'Elemento de prueba 04', 'Elemento de prueba 05', 'Elemento de prueba 06']
        for i, name in enumerate(names):
            pid = WORKER_ID if i == 0 else str(uuid4())
            self.people[pid] = {'id': pid, 'cuip': f'DEMO{i+1:05}', 'curp': None, 'nombre_completo': name,
                'sexo': None, 'corporacion_id': CORP_A if i < 4 else CORP_B,
                'adscripcion': 'Unidad de demostración', 'cargo_id': None, 'grado_id': None, 'estatus': 'activo'}
            if i == 4: continue
            end = hoy_local() + timedelta(days=[-25, 35, 75, 400, 0, 600][i])
            cert = end.replace(year=end.year - 3, day=min(end.day, 28))
            self.evaluations.append({'id': str(uuid4()), 'personal_id': pid, 'fecha_certificacion': cert.isoformat(),
                'institucion_evaluadora': 'Institución de prueba', 'folio': f'DEMO-CB-{i+1:03}',
                'resultado': 'no_aprobado' if i == 5 else 'aprobado', 'activo': True})

class DemoRepository:
    def __init__(self, store, user):
        self.store, self.user = store, user

    def allowed(self, pid):
        return self.user['rol'] != 'trabajador' or self.user['personal_id'] == pid

    def catalogs(self): return deepcopy(self.store.catalogs)
    def config(self): return {'dias_alerta': 90}

    def row(self, p):
        active = next((e for e in self.store.evaluations if e['personal_id'] == p['id'] and e['activo']), None)
        corp = next(c['nombre'] for c in self.store.catalogs['corporaciones'] if c['id'] == p['corporacion_id'])
        return {**deepcopy(p), 'personal_id': p['id'], 'corporacion': corp, 'cargo': None, 'grado': None,
                'competencia_id': active['id'] if active else None,
                'fecha_certificacion': active['fecha_certificacion'] if active else None,
                'resultado': active['resultado'] if active else None, **detalle_vigencia(active)}

    def list_personal(self, *, q='', estatus='', corporacion_id='', vigencia='', offset=0, limit=25):
        with self.store.lock:
            rows = [self.row(p) for p in self.store.people.values() if self.allowed(p['id'])]
        rows = [p for p in rows if (not q or any(q.lower() in str(p.get(k) or '').lower() for k in ('nombre_completo','cuip','curp')))
                and (not estatus or p['estatus'] == estatus) and (not corporacion_id or p['corporacion_id'] == corporacion_id)
                and (not vigencia or p['estatus_vigencia'] == vigencia)]
        return sorted(rows, key=lambda p: (p['nombre_completo'], p['personal_id']))[offset:offset + limit]

    def get_personal(self, person_id):
        with self.store.lock:
            if person_id not in self.store.people or not self.allowed(person_id):
                raise HTTPException(404, 'Expediente no encontrado.')
            return self.row(self.store.people[person_id])

    def save_personal(self, data, person_id=None):
        with self.store.lock:
            if person_id and person_id not in self.store.people: raise HTTPException(404, 'Expediente no encontrado.')
            for field, table in [('corporacion_id','corporaciones'), ('cargo_id','cargos'), ('grado_id','grados')]:
                if data.get(field) and not any(c['id'] == data[field] for c in self.store.catalogs[table]):
                    raise HTTPException(422, 'El catálogo seleccionado no existe.')
            for other in self.store.people.values():
                if other['id'] != person_id and any(data.get(k) and data[k] == other.get(k) for k in ('cuip','curp')):
                    raise HTTPException(409, 'Ya existe el identificador registrado.')
            pid = person_id or str(uuid4())
            self.store.people[pid] = {**deepcopy(data), 'id': pid}
            return deepcopy(self.store.people[pid])

    def history(self, person_id):
        self.get_personal(person_id)
        with self.store.lock:
            return [{**deepcopy(e), 'fecha_vencimiento': detalle_vigencia(e)['fecha_vencimiento']}
                    for e in sorted(self.store.evaluations, key=lambda e:e['fecha_certificacion'], reverse=True) if e['personal_id'] == person_id]

    def add_competencia(self, data):
        with self.store.lock:
            self.get_personal(data['personal_id'])
            history = [e for e in self.store.evaluations if e['personal_id'] == data['personal_id']]
            if any(e['fecha_certificacion'] == data['fecha_certificacion'] and e['folio'] == data['folio'] for e in history):
                raise HTTPException(409, 'La evaluación ya está registrada.')
            current = next((e for e in history if e['activo']), None)
            active = not current or data['fecha_certificacion'] >= current['fecha_certificacion']
            if active and current: current['activo'] = False
            row = {**deepcopy(data), 'id': str(uuid4()), 'activo': active}
            self.store.evaluations.append(row)
            return {**row, 'fecha_vencimiento': detalle_vigencia(row)['fecha_vencimiento']}

    def summary(self):
        rows = self.list_personal(estatus='activo', limit=100000)
        return {'total': len(rows), **{s: sum(r['estatus_vigencia'] == s for r in rows)
                for s in ['Vigente','Por vencer','Vencida','Sin registro','No aprobado']}}

store = DemoStore()
