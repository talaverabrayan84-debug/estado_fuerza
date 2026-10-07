from io import BytesIO
from zipfile import ZipFile
import re

import pytest
from openpyxl import Workbook

from app.db.supabase_client import SupabaseRepository
from app.services.vigencia import hoy_local


@pytest.mark.parametrize('extension', ['csv', 'xlsx'])
def test_long_valid_import_filename_keeps_its_format(client, auth, extension):
    headers = ['cuip', 'nombre_completo', 'corporacion', 'adscripcion']
    values = ['QA001', 'Persona ficticia QA', 'Corporación de ejemplo A', 'Unidad QA']
    if extension == 'xlsx':
        book = Workbook()
        book.active.append(headers)
        book.active.append(values)
        out = BytesIO()
        book.save(out)
        book.close()
        content = out.getvalue()
    else:
        content = (','.join(headers) + '\n' + ','.join(values)).encode('utf8')
    response = client.post('/api/carga-masiva/previsualizar', headers=auth(),
                           data={'destino': 'personal'},
                           files={'archivo': ('a' * 205 + '.' + extension, content)})
    assert response.status_code == 201, response.text
    record = response.json()
    assert record['registros_error'] == 0
    assert len(record['nombre_archivo']) <= 200
    assert record['nombre_archivo'].endswith('.' + extension)


def test_long_valid_evidence_filename_is_accepted(client, auth):
    worker = auth('trabajador')
    entry = client.post('/api/bitacora', headers=worker, json={
        'fecha': hoy_local().isoformat(), 'tipo_actividad': 'entrega',
        'descripcion': 'Comprobante ficticio de prueba QA'
    }).json()
    path = f"/api/bitacora/{entry['id']}/evidencia"
    content = b'%PDF-1.4\n%%EOF'
    response = client.post(path, headers=worker,
                           files={'archivo': ('a' * 205 + '.pdf', content)})
    assert response.status_code == 201, response.text
    metadata = client.get(path, headers=worker).json()
    assert len(metadata['nombre']) <= 200
    assert metadata['nombre'].endswith('.pdf')
    assert client.get(path + '/descargar', headers=worker).content == content


def test_history_does_not_lose_evaluations_at_postgrest_row_limit(monkeypatch):
    expected = [{'id': str(i), 'folio': f'QA-{i}'} for i in range(1105)]
    def request(self, method, path, *, params=None, json=None):
        assert method == 'GET' and path == '/rest/v1/competencias_basicas'
        offset = int(params.get('offset', 0))
        limit = min(int(params.get('limit', 1000)), 1000)
        return expected[offset:offset + limit]
    monkeypatch.setattr(SupabaseRepository, 'request', request)
    assert SupabaseRepository('dummy-test-token').history('dummy-person-id') == expected


def test_corrupt_excel_date_cannot_be_confirmed(client, auth):
    from datetime import date
    book = Workbook()
    book.active.append(['cuip', 'institucion_evaluadora', 'fecha_certificacion', 'resultado', 'folio'])
    book.active.append(['DEMO00001', 'Academia ficticia', date(2020, 1, 1), 'aprobado', 'QA-FOLIO'])
    original = BytesIO()
    book.save(original)
    book.close()
    altered = BytesIO()
    with ZipFile(BytesIO(original.getvalue())) as source, ZipFile(altered, 'w') as target:
        for entry in source.infolist():
            data = source.read(entry.filename)
            if entry.filename == 'xl/worksheets/sheet1.xml':
                data = re.sub(rb'(<c r="C2"[^>]*><v>)[^<]+(</v>)', rb'\g<1>1e999\2', data)
            target.writestr(entry, data)
    response = client.post('/api/carga-masiva/previsualizar', headers=auth(),
                           data={'destino': 'competencias_basicas'},
                           files={'archivo': ('fecha-corrupta.xlsx', altered.getvalue())})
    assert response.status_code == 201, response.text
    record = response.json()
    assert record['registros_error'] == 1
    assert client.post(f"/api/carga-masiva/{record['id']}/confirmar", headers=auth()).status_code == 422


def test_latest_same_day_evaluation_is_shown_first_in_demo(client, auth):
    from app.db.demo import WORKER_ID
    headers = auth()
    for folio in ['QA-FIRST', 'QA-SECOND']:
        response = client.post('/api/competencias-basicas', headers=headers, json={
            'personal_id': WORKER_ID, 'institucion_evaluadora': 'Academia ficticia',
            'fecha_certificacion': hoy_local().isoformat(), 'resultado': 'aprobado', 'folio': folio})
        assert response.status_code == 201, response.text
    rows = client.get(f'/api/competencias-basicas/{WORKER_ID}', headers=headers).json()
    assert rows[0]['folio'] == 'QA-SECOND' and rows[0]['activo']
    assert rows[1]['folio'] == 'QA-FIRST' and not rows[1]['activo']


def test_demo_person_detail_shows_assigned_catalog_names(client, auth):
    from app.db import demo
    cargo_id = '30000000-0000-0000-0000-000000000001'
    grado_id = '30000000-0000-0000-0000-000000000002'
    demo.store.catalogs['cargos'].append({'id': cargo_id, 'nombre': 'Cargo ficticio QA', 'activo': True})
    demo.store.catalogs['grados'].append({'id': grado_id, 'nombre': 'Grado ficticio QA', 'activo': True})
    headers = auth()
    person = client.post('/api/personal', headers=headers, json={
        'nombre_completo': 'Persona ficticia QA', 'cuip': 'QACATALOG001',
        'corporacion_id': demo.CORP_A, 'adscripcion': 'Unidad QA',
        'cargo_id': cargo_id, 'grado_id': grado_id}).json()
    details = client.get(f"/api/personal/{person['id']}", headers=headers).json()
    assert details['cargo'] == 'Cargo ficticio QA'
    assert details['grado'] == 'Grado ficticio QA'


@pytest.mark.parametrize('value', [0, '0', 86400, '1970-01-01T00:00:00Z'])
def test_calendar_dates_are_not_silently_converted_from_timestamps(client, auth, value):
    from app.db.demo import WORKER_ID
    response = client.post('/api/competencias-basicas', headers=auth(), json={
        'personal_id': WORKER_ID, 'institucion_evaluadora': 'Academia ficticia',
        'fecha_certificacion': value, 'resultado': 'aprobado', 'folio': 'QA-DATE'})
    assert response.status_code == 422, response.text


def test_csv_numeric_date_is_flagged_instead_of_creating_a_1970_evaluation(client, auth):
    headers = auth()
    content = b'cuip,institucion_evaluadora,fecha_certificacion,resultado,folio\nDEMO00001,Academia QA,0,aprobado,QA-DATE'
    response = client.post('/api/carga-masiva/previsualizar', headers=headers,
                           data={'destino': 'competencias_basicas'}, files={'archivo': ('fecha.csv', content)})
    assert response.status_code == 201, response.text
    assert response.json()['registros_error'] == 1


def test_calendar_range_rejects_timestamp_numbers(client, auth):
    response = client.get('/api/curso-sesiones?desde=0&hasta=86400', headers=auth())
    assert response.status_code == 422, response.text


def test_session_and_journal_reject_numeric_calendar_dates(client, auth):
    from app.db import demo
    course_id = next(iter(demo.store.courses))
    response = client.post('/api/curso-sesiones', headers=auth(), json={
        'curso_id': course_id, 'fecha_inicio': 0, 'fecha_fin': 86400,
        'sede': 'Aula ficticia', 'modalidad': 'presencial', 'cupo': 1})
    assert response.status_code == 422, response.text
    response = client.post('/api/bitacora', headers=auth('trabajador'), json={
        'fecha': '0', 'tipo_actividad': 'avance', 'descripcion': 'Actividad ficticia'})
    assert response.status_code == 422, response.text


@pytest.mark.parametrize('today, expected', [('2026-09-25', '2026-10-30'),
                                          ('2026-09-26', '2026-10-31'),
                                          ('2024-01-25', '2024-02-28')])
def test_demo_seed_keeps_month_end_except_when_leap_day_is_unrepresentable(monkeypatch, today, expected):
    from datetime import date
    from app.db import demo
    from app.services.vigencia import detalle_vigencia
    monkeypatch.setattr(demo, 'hoy_local', lambda: date.fromisoformat(today))
    store = demo.DemoStore()
    assert detalle_vigencia(store.evaluations[1])['fecha_vencimiento'] == expected
