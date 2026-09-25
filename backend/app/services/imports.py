"""Bounded, non-executing CSV/XLSX import and preview validation."""
import csv
import re
from collections import Counter
from datetime import date, datetime
from io import BytesIO, StringIO
from pathlib import PurePath
from zipfile import ZipFile, BadZipFile
from xml.etree.ElementTree import ParseError
from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import iterparse
from fastapi import HTTPException
from pydantic import ValidationError
from app.schemas import PersonalIn, CompetenciaIn

MAX_BYTES=2*1024*1024
MAX_ROWS=200


def validate_sheet_xml(archive, worksheet_path):
    """Do not trust XLSX dimension hints: reject cells outside import bounds."""
    ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    with archive.open(worksheet_path) as stream:
        for _, element in iterparse(stream, events=('end',)):
            if element.tag == ns + 'row':
                number = element.get('r', '')
                if not number.isdigit() or not 1 <= int(number) <= MAX_ROWS + 1:
                    raise ValueError('Máximo 200 filas por archivo.')
            elif element.tag == ns + 'c':
                coordinate = re.fullmatch(r'([A-T])([1-9][0-9]*)', element.get('r', ''))
                if not coordinate or int(coordinate[2]) > MAX_ROWS + 1:
                    raise ValueError('Máximo 200 filas y 20 columnas por archivo.')
            element.clear()

HEADERS={
 'personal':['cuip','curp','nombre_completo','sexo','corporacion','adscripcion','cargo','grado','estatus'],
 'competencias_basicas':['cuip','curp','institucion_evaluadora','fecha_certificacion','resultado','folio']
}
REQUIRED={'personal':{'nombre_completo','corporacion','adscripcion'},
          'competencias_basicas':{'institucion_evaluadora','fecha_certificacion','resultado','folio'}}

def target_valid(target):
    if target not in HEADERS: raise HTTPException(422,'Destino no admitido.')

def cell_text(value):
    if value is None: return ''
    if isinstance(value,(date,datetime)): return value.date().isoformat() if isinstance(value,datetime) else value.isoformat()
    return str(value).strip()

def read_file(content: bytes, filename: str, target: str):
    target_valid(target)
    if not content or len(content)>MAX_BYTES: raise HTTPException(413,'El archivo debe contener datos y pesar como máximo 2 MB.')
    suffix=PurePath(filename.lower()).suffix
    try:
        if suffix=='.csv':
            try: text=content.decode('utf-8-sig')
            except UnicodeDecodeError: text=content.decode('cp1252')
            if '\x00' in text: raise ValueError('Archivo CSV inválido.')
            try: dialect=csv.Sniffer().sniff(text[:4096],delimiters=',;\t')
            except csv.Error: dialect=csv.excel
            grid=[]; numbers=[]
            reader=csv.reader(StringIO(text),dialect)
            for row in reader:
                if any(cell_text(x) for x in row):
                    grid.append(row); numbers.append(reader.line_num)
                if len(grid)>MAX_ROWS+1: raise ValueError('Máximo 200 filas por archivo. Divida la carga en lotes.')
        elif suffix=='.xlsx':
            with ZipFile(BytesIO(content)) as archive:
                if sum(i.file_size for i in archive.infolist())>20*1024*1024 or len(archive.infolist())>2000:
                    raise ValueError('El libro excede el tamaño permitido al descomprimir.')
                if any('vbaproject' in i.filename.lower() for i in archive.infolist()): raise ValueError('No se admiten macros.')
            from openpyxl import load_workbook
            book=load_workbook(BytesIO(content),read_only=True,data_only=False,keep_links=False)
            try:
                if len(book.worksheets)!=1: raise ValueError('Use un libro con una sola hoja de datos.')
                sheet=book.worksheets[0]
                if (sheet.max_row or 0)>MAX_ROWS+1 or (sheet.max_column or 0)>20: raise ValueError('Máximo 200 filas y 20 columnas por archivo.')
                with ZipFile(BytesIO(content)) as archive:
                    # Use the part resolved by openpyxl, including nonstandard paths.
                    validate_sheet_xml(archive, sheet._worksheet_path)
                # Some spreadsheet writers report A1:A1 despite having more cells.
                sheet.reset_dimensions()
                grid=[]; numbers=[]
                for n,row in enumerate(sheet.iter_rows(max_col=20),1):
                    values=[cell_text(c.value) for c in row]
                    if any(values): grid.append(values); numbers.append(n)
                width=max((i+1 for row in grid for i,v in enumerate(row) if v),default=0)
                grid=[row[:width] for row in grid]
            finally: book.close()
        else: raise ValueError('Use un archivo .xlsx o .csv.')
        if len(grid)<2: raise ValueError('El archivo debe incluir encabezados y al menos una fila.')
        headers=[cell_text(h).lower() for h in grid[0]]
        if len(headers)>20 or '' in headers or len(set(headers))!=len(headers): raise ValueError('Encabezados vacíos, duplicados o demasiadas columnas.')
        unknown=set(headers)-set(HEADERS[target])
        missing=REQUIRED[target]-set(headers)
        if unknown: raise ValueError('Columnas no admitidas: '+', '.join(sorted(unknown)))
        if missing: raise ValueError('Faltan columnas: '+', '.join(sorted(missing)))
        if not {'cuip','curp'} & set(headers): raise ValueError('Incluya una columna CUIP o CURP.')
        rows=[]
        for number,row in zip(numbers[1:],grid[1:]):
            if len(row)!=len(headers): raise ValueError(f'Fila {number}: el número de columnas no coincide.')
            values={k:cell_text(v) for k,v in zip(headers,row)}
            if any(len(v)>5000 for v in values.values()): raise ValueError(f'Fila {number}: una celda excede 5000 caracteres.')
            rows.append((number,values))
        return rows
    except HTTPException: raise
    except (ValueError,KeyError,csv.Error,BadZipFile,OSError,UnicodeError,ParseError,DefusedXmlException) as e:
        raise HTTPException(422,str(e) if isinstance(e,ValueError) else 'El archivo está dañado o tiene un formato inválido.')

def build_preview(rows, target, repo):
    ids={k:{r.get(k,'').upper() for _,r in rows if re.fullmatch(r'[A-Za-z0-9]{1,20}',r.get(k,''))} for k in ('cuip','curp')}
    people=repo.lookup_people(ids['cuip'],ids['curp'])
    indexes={k:{p[k]:p for p in people if p.get(k)} for k in ('cuip','curp')}
    catalogs=repo.catalogs() if target=='personal' else {}
    evaluations=repo.lookup_evaluations({p['id'] for p in people}) if target!='personal' else []
    evaluation_keys={(e['personal_id'],e['fecha_certificacion'],e['folio']) for e in evaluations}
    duplicate_keys={k:Counter(r.get(k,'').upper() for _,r in rows if r.get(k)) for k in ('cuip','curp')}
    preview=[]
    for number,raw in rows:
        errors=[]; data={}; matches={}
        for k in ('cuip','curp'):
            ident=raw.get(k,'').upper()
            if ident in indexes[k]: matches[indexes[k][ident]['id']]=indexes[k][ident]
            if ident and duplicate_keys[k][ident]>1 and target=='personal': errors.append(f'{k.upper()} duplicado dentro del archivo.')
        person=next(iter(matches.values()),None)
        if len(matches)>1: errors.append('CUIP y CURP corresponden a personas distintas.')
        if any(v.startswith(('=','+','@')) for v in raw.values()): errors.append('No se admiten fórmulas ni celdas que comiencen con =, + o @.')
        try:
            missing=[k for k in REQUIRED[target] if not raw.get(k)]
            if missing: raise ValueError('Campos obligatorios vacíos: '+', '.join(sorted(missing)))
            # Validate both supplied identifiers, including when importing evaluations.
            if not raw.get('cuip') and not raw.get('curp'): raise ValueError('Capture CUIP o CURP.')
            for k in ('cuip','curp'):
                if raw.get(k):
                    if k=='cuip': PersonalIn.check_cuip(raw[k].upper())
                    else: PersonalIn.check_curp(raw[k].upper())
            if target=='personal':
                baseline={k:person[k] for k in PersonalIn.model_fields if person and k in person}
                baseline.update({k:v for k,v in raw.items() if k in PersonalIn.model_fields and v})
                for src,dest in [('corporacion','corporacion_id'),('cargo','cargo_id'),('grado','grado_id')]:
                    if raw.get(src):
                        table={'corporacion':'corporaciones','cargo':'cargos','grado':'grados'}[src]
                        found=[c for c in catalogs[table] if c['nombre'].casefold()==raw[src].casefold() and c['activo']]
                        if len(found)!=1: raise ValueError(f'{src.capitalize()} no existe o está inactivo: {raw[src]}')
                        baseline[dest]=found[0]['id']
                data=PersonalIn(**baseline).model_dump(mode='json')
            else:
                if not person: raise ValueError('No se encontró un expediente con ese CUIP o CURP.')
                if any(raw.get(k) and person.get(k)!=raw[k].upper() for k in ('cuip','curp')):
                    raise ValueError('Los identificadores no coinciden con el expediente.')
                data=CompetenciaIn(**{k:v for k,v in raw.items() if k not in ('cuip','curp')},personal_id=person['id']).model_dump(mode='json')
                if (person['id'],data['fecha_certificacion'],data['folio']) in evaluation_keys:
                    errors.append('La evaluación ya existe en el expediente.')
        except ValidationError as e:
            errors.extend('.'.join(str(x) for x in err['loc'])+': '+err['msg'].replace('Value error, ','') for err in e.errors())
        except ValueError as e: errors.append(str(e))
        preview.append({'fila':number,'identificador':raw.get('cuip') or raw.get('curp') or '',
            'accion':'actualizar' if person and target=='personal' else 'insertar','personal_id':person['id'] if person else None,
            'version':person.get('updated_at') if person else None,'datos':data,'origen':raw,'errores':errors})
    # Different identifiers can still refer to the same person.
    keys=Counter((r['personal_id'],r['datos'].get('fecha_certificacion'),r['datos'].get('folio')) if target!='personal' else r['personal_id'] for r in preview if r['personal_id'])
    for r in preview:
        key=(r['personal_id'],r['datos'].get('fecha_certificacion'),r['datos'].get('folio')) if target!='personal' else r['personal_id']
        if r['personal_id'] and keys[key]>1: r['errores'].append('Registro repetido en el archivo.')
    return preview

def template(target):
    target_valid(target)
    out=StringIO(); csv.writer(out).writerow(HEADERS[target])
    return out.getvalue().encode('utf-8-sig')
