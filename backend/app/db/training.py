"""Supabase operations keep the requesting user's JWT and database RLS."""
class TrainingRepository:
    def courses(self, offset=0, limit=101):
        return self.request('GET', '/rest/v1/cursos', params={'select':'*','order':'nombre_curso,id','offset':offset,'limit':limit})

    def save_course(self, data, course_id=None):
        from fastapi import HTTPException
        rows=self.request('PATCH' if course_id else 'POST','/rest/v1/cursos',
                            params={'id':f'eq.{course_id}'} if course_id else None,json=data)
        if not rows: raise HTTPException(404,'Curso no encontrado.')
        return rows[0]

    def lookup_evaluations(self, person_ids):
        if not person_ids: return []
        # Fetch by person in bounded pages: histories can exceed PostgREST's row cap.
        rows=[]; offset=0
        while True:
            page=self.request('GET','/rest/v1/competencias_basicas',params={'select':'personal_id,fecha_certificacion,folio',
                'personal_id':'in.('+','.join(sorted(person_ids))+')','order':'id','offset':offset,'limit':500})
            rows.extend(page)
            if len(page)<500: return rows
            offset+=500

    def sessions(self, start, end, offset=0, limit=501):
        return self.request('GET','/rest/v1/vw_curso_sesiones',params={
            'select':'*','fecha_inicio':f'lte.{end}','fecha_fin':f'gte.{start}',
            'order':'fecha_inicio,id','offset':offset,'limit':limit})

    def session(self, session_id):
        from fastapi import HTTPException
        rows=self.request('GET','/rest/v1/vw_curso_sesiones',params={'id':f'eq.{session_id}','select':'*'})
        if not rows: raise HTTPException(404,'Sesión no encontrada.')
        return rows[0]

    def save_session(self, data, session_id=None):
        from fastapi import HTTPException
        rows=self.request('PATCH' if session_id else 'POST','/rest/v1/curso_sesiones',
                          params={'id':f'eq.{session_id}'} if session_id else None,json=data)
        if not rows: raise HTTPException(404,'Sesión no encontrada.')
        return rows[0]

    def enrollments(self, session_id=None, person_id=None, offset=0, limit=101):
        params={'select':'*,personal(nombre_completo,cuip,curp),curso_sesiones(fecha_inicio,fecha_fin,cursos(nombre_curso))',
                'order':'fecha_inscripcion.desc,id','offset':offset,'limit':limit}
        if session_id: params['sesion_id']=f'eq.{session_id}'
        if person_id: params['personal_id']=f'eq.{person_id}'
        return self.request('GET','/rest/v1/inscripciones',params=params)

    def enroll(self, session_id, data):
        return self.request('POST','/rest/v1/rpc/guardar_inscripcion',json={'sesion':session_id,'datos':data})

    def journal(self, person_id, offset=0, limit=26):
        return self.request('GET','/rest/v1/bitacora',params={'personal_id':f'eq.{person_id}',
            'select':'*,curso_sesiones(cursos(nombre_curso))','order':'fecha.desc,created_at.desc,id',
            'offset':offset,'limit':limit})

    def journal_entry(self, entry_id):
        from fastapi import HTTPException
        rows=self.request('GET','/rest/v1/bitacora',params={'id':f'eq.{entry_id}','select':'*'})
        if not rows: raise HTTPException(404,'Entrada no encontrada.')
        return rows[0]

    def save_journal(self, data, entry_id=None):
        return self.request('POST','/rest/v1/rpc/guardar_bitacora',json={'datos':data,'entrada':entry_id})

    def lookup_people(self, cuips, curps):
        # Inputs have been constrained to letters/digits by the import validator.
        clauses=[]
        if cuips: clauses.append('cuip.in.('+','.join(sorted(cuips))+')')
        if curps: clauses.append('curp.in.('+','.join(sorted(curps))+')')
        if not clauses: return []
        return self.request('GET','/rest/v1/personal',params={'select':'*','or':'('+','.join(clauses)+')','limit':1000})

    def stage_import(self, data):
        return self.request('POST','/rest/v1/rpc/preparar_carga',json={'datos':data})

    def imports(self, offset=0, limit=26):
        return self.request('GET','/rest/v1/carga_archivos',params={'select':'id,nombre_archivo,tabla_destino,estado,registros_procesados,registros_error,fecha_carga,expires_at',
            'order':'fecha_carga.desc,id','offset':offset,'limit':limit})

    def import_detail(self, import_id):
        from fastapi import HTTPException
        rows=self.request('GET','/rest/v1/carga_archivos',params={'id':f'eq.{import_id}','select':'*'})
        if not rows: raise HTTPException(404,'Carga no encontrada.')
        return rows[0]

    def confirm_import(self, import_id):
        return self.request('POST','/rest/v1/rpc/confirmar_carga',json={'carga':import_id})
