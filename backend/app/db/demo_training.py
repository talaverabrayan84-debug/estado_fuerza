from copy import deepcopy
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import HTTPException
from app.services.cursos import estatus_sesion
from app.services.vigencia import hoy_local

def timestamp():
    return datetime.now(timezone.utc).isoformat()

def initialize_training(store):
    cid, sid = str(uuid4()), str(uuid4())
    store.courses = {cid: dict(id=cid, nombre_curso='Actualización en actuación policial',
        tipo='actualizacion', fuente_financiamiento='recurso_propio',
        institucion_impartidora='Academia de demostración', horas=40, vigencia_meses=None)}
    store.sessions = {sid: dict(id=sid, curso_id=cid, fecha_inicio=hoy_local().isoformat(),
        fecha_fin=(hoy_local()+timedelta(days=4)).isoformat(), sede='Aula de demostración',
        modalidad='presencial', cupo=25)}
    pid = next(iter(store.people))
    eid = str(uuid4())
    store.enrollments = {eid: dict(id=eid, personal_id=pid, sesion_id=sid,
        fecha_inscripcion=hoy_local().isoformat(), estatus='inscrito', calificacion=None)}
    store.journal, store.imports, store.evidence = {}, {}, {}
    for name,offset,kind,source in [('Primeros auxilios',7,'actualizacion','FASP'),('Competencias básicas de la función policial',-10,'competencias_basicas','FOFISP')]:
        course_id,session_id=str(uuid4()),str(uuid4())
        store.courses[course_id]=dict(id=course_id,nombre_curso=name,tipo=kind,fuente_financiamiento=source,
            institucion_impartidora='Academia de demostración',horas=40,vigencia_meses=36 if kind=='competencias_basicas' else None)
        store.sessions[session_id]=dict(id=session_id,curso_id=course_id,
            fecha_inicio=(hoy_local()+timedelta(days=offset)).isoformat(),fecha_fin=(hoy_local()+timedelta(days=offset+2)).isoformat(),
            sede='Centro de capacitación ficticio',modalidad='presencial',cupo=30)

class DemoTraining:
    def courses(self, offset=0, limit=101):
        with self.store.lock:
            return deepcopy(sorted(self.store.courses.values(), key=lambda c:(c['nombre_curso'],c['id']))[offset:offset+limit])

    def save_course(self, data, course_id=None):
        with self.store.lock:
            if course_id and course_id not in self.store.courses: raise HTTPException(404,'Curso no encontrado.')
            cid=course_id or str(uuid4())
            self.store.courses[cid]={**deepcopy(data),'id':cid}
            return deepcopy(self.store.courses[cid])

    def session(self, session_id):
        with self.store.lock:
            s=self.store.sessions.get(session_id)
            if not s: raise HTTPException(404,'Sesión no encontrada.')
            course=self.store.courses[s['curso_id']]
            count=sum(e['sesion_id']==session_id and e['estatus']!='baja' and self.allowed(e['personal_id']) for e in self.store.enrollments.values())
            return deepcopy({**course,**s,'estatus':estatus_sesion(s['fecha_inicio'],s['fecha_fin']),'inscripciones_visibles':count})

    def sessions(self, start, end, offset=0, limit=501):
        with self.store.lock:
            rows=[self.session(s['id']) for s in self.store.sessions.values() if s['fecha_inicio']<=end and s['fecha_fin']>=start]
            return sorted(rows,key=lambda s:(s['fecha_inicio'],s['id']))[offset:offset+limit]

    def save_session(self, data, session_id=None):
        with self.store.lock:
            if session_id and session_id not in self.store.sessions: raise HTTPException(404,'Sesión no encontrada.')
            if data['curso_id'] not in self.store.courses: raise HTTPException(422,'Curso no encontrado.')
            occupied=sum(e['sesion_id']==session_id and e['estatus']!='baja' for e in self.store.enrollments.values())
            if occupied>data['cupo']: raise HTTPException(409,'El cupo es menor que las inscripciones activas.')
            sid=session_id or str(uuid4())
            self.store.sessions[sid]={**deepcopy(data),'id':sid}
            return deepcopy(self.store.sessions[sid])

    def enrollments(self, session_id=None, person_id=None, offset=0, limit=101):
        with self.store.lock:
            rows=[]
            for e in self.store.enrollments.values():
                if not self.allowed(e['personal_id']) or (session_id and e['sesion_id']!=session_id) or (person_id and e['personal_id']!=person_id): continue
                s=self.session(e['sesion_id'])
                rows.append({**deepcopy(e),'personal':deepcopy(self.store.people[e['personal_id']]),
                    'curso_sesiones':{**s,'cursos':{'nombre_curso':s['nombre_curso']}}})
            rows.sort(key=lambda e:e['id'])
            return sorted(rows,key=lambda e:e['fecha_inscripcion'],reverse=True)[offset:offset+limit]

    def enroll(self, session_id, data):
        with self.store.lock:
            self.session(session_id); self.get_personal(data['personal_id'])
            old=next((e for e in self.store.enrollments.values() if e['sesion_id']==session_id and e['personal_id']==data['personal_id']),None)
            occupied=sum(e['sesion_id']==session_id and e['estatus']!='baja' for e in self.store.enrollments.values())
            if (not old or old['estatus']=='baja') and data['estatus']!='baja' and occupied>=self.store.sessions[session_id]['cupo']:
                raise HTTPException(409,'No hay cupo disponible.')
            eid=old['id'] if old else str(uuid4())
            row={**deepcopy(data),'id':eid,'sesion_id':session_id,'fecha_inscripcion':old['fecha_inscripcion'] if old else hoy_local().isoformat()}
            self.store.enrollments[eid]=row
            return deepcopy(row)

    def journal_entry(self, entry_id):
        with self.store.lock:
            e=self.store.journal.get(entry_id)
            if not e or not self.allowed(e['personal_id']): raise HTTPException(404,'Entrada no encontrada.')
            return deepcopy(e)

    def journal(self, person_id, offset=0, limit=26):
        self.get_personal(person_id)
        with self.store.lock:
            rows=[deepcopy(e) for e in self.store.journal.values() if e['personal_id']==person_id]
            for e in rows:
                e['curso_sesiones']={'cursos':{'nombre_curso':self.session(e['sesion_id'])['nombre_curso']}} if e['sesion_id'] else None
            rows.sort(key=lambda e:e['id'])
            return sorted(rows,key=lambda e:(e['fecha'],e['created_at']),reverse=True)[offset:offset+limit]

    def save_journal(self, data, entry_id=None):
        with self.store.lock:
            pid=self.user['personal_id']
            if self.user['rol']!='trabajador' or not pid: raise HTTPException(403,'Sin permiso.')
            sid=data.get('sesion_id')
            if sid and not any(e['personal_id']==pid and e['sesion_id']==sid and e['estatus']!='baja' for e in self.store.enrollments.values()):
                raise HTTPException(403,'Se requiere inscripción en la sesión.')
            old=self.journal_entry(entry_id) if entry_id else None
            if old and old['creado_por']!=self.user['id']: raise HTTPException(403,'Entrada no disponible.')
            eid=entry_id or str(uuid4())
            row={**(old or {}),**deepcopy(data),'id':eid,'personal_id':pid,'creado_por':self.user['id'],
                'created_at':old['created_at'] if old else timestamp(),'updated_at':timestamp()}
            self.store.journal[eid]=row
            return deepcopy(row)

    def lookup_people(self, cuips, curps):
        with self.store.lock:
            return deepcopy([p for p in self.store.people.values() if p.get('cuip') in cuips or p.get('curp') in curps])

    def lookup_evaluations(self, person_ids):
        with self.store.lock:
            return deepcopy([e for e in self.store.evaluations if e['personal_id'] in person_ids])

    def stage_import(self, data):
        with self.store.lock:
            iid=str(uuid4())
            row={**deepcopy(data),'id':iid,'usuario_id':self.user['id'],'estado':'revision',
                'registros_procesados':0,'registros_error':sum(bool(r['errores']) for r in data['filas']),
                'fecha_carga':timestamp(),'expires_at':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()}
            self.store.imports[iid]=row
            return deepcopy(row)

    def imports(self, offset=0, limit=26):
        with self.store.lock:
            rows=[deepcopy(r) for r in self.store.imports.values() if r['usuario_id']==self.user['id']]
            rows.sort(key=lambda r:r['id'])
            return sorted(rows,key=lambda r:r['fecha_carga'],reverse=True)[offset:offset+limit]

    def import_detail(self, import_id):
        with self.store.lock:
            row=self.store.imports.get(import_id)
            if not row or row['usuario_id']!=self.user['id']: raise HTTPException(404,'Carga no encontrada.')
            return deepcopy(row)

    def confirm_import(self, import_id):
        with self.store.lock:
            row=self.import_detail(import_id)
            if row['estado']=='confirmada': return row
            if datetime.fromisoformat(row['expires_at'])<=datetime.now(timezone.utc): raise HTTPException(409,'La revisión ha caducado. Vuelva a cargar el archivo.')
            if row['registros_error']: raise HTTPException(422,'Corrija todas las filas antes de confirmar.')
            people, evaluations=deepcopy(self.store.people),deepcopy(self.store.evaluations)
            try:
                for r in row['filas']:
                    if row['tabla_destino']=='personal':
                        pid=r['personal_id']
                        if pid and (pid not in self.store.people or self.store.people[pid]['updated_at']!=r['version']):
                            raise HTTPException(409,'Un expediente cambió desde la revisión. Vuelva a cargar el archivo.')
                        self.save_personal(r['datos'],pid)
                    else: self.add_competencia(r['datos'])
            except Exception:
                self.store.people,self.store.evaluations=people,evaluations
                raise
            row.update(estado='confirmada',registros_procesados=len(row['filas']),confirmado_at=timestamp())
            self.store.imports[import_id]=row
            return deepcopy(row)
