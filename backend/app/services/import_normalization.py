"""Explicit, deterministic import normalization; never guess identities."""
import re
import unicodedata
from datetime import datetime


def clean_text(value):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', value)).strip()


def match_key(value):
    value = unicodedata.normalize('NFKD', clean_text(value).casefold())
    value = ''.join(c for c in value if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', '_', value).strip('_')


ALIASES = {
    'cuip': ['cuip', 'clave unica de identificacion policial'],
    'curp': ['curp', 'clave unica de registro de poblacion'],
    'nombre_completo': ['nombre completo', 'nombre', 'nombre del elemento', 'nombre del personal'],
    'sexo': ['sexo', 'genero'],
    'corporacion': ['corporacion', 'institucion policial', 'dependencia'],
    'adscripcion': ['adscripcion', 'unidad', 'unidad de adscripcion'],
    'cargo': ['cargo', 'puesto'],
    'grado': ['grado', 'grado policial', 'rango'],
    'estatus': ['estatus', 'estado', 'situacion', 'estatus del personal'],
    'institucion_evaluadora': ['institucion evaluadora', 'academia', 'evaluadora'],
    'fecha_certificacion': ['fecha certificacion', 'fecha de certificacion', 'fecha de evaluacion'],
    'resultado': ['resultado', 'resultado evaluacion', 'resultado de evaluacion'],
    'folio': ['folio', 'folio de certificacion', 'numero de folio'],
}
HEADER_FIELDS = {match_key(alias): field for field, aliases in ALIASES.items() for alias in aliases}


def normalize_row(raw):
    normalized = {key: clean_text(value) for key, value in raw.items()}
    for key in ('cuip', 'curp'):
        if key in normalized:
            normalized[key] = normalized[key].upper()
    options = {
        'sexo': {'h': 'H', 'hombre': 'H', 'masculino': 'H', 'm': 'M', 'mujer': 'M', 'femenino': 'M'},
        'estatus': {key: key for key in ('activo', 'baja', 'comisionado', 'licencia')},
        'resultado': {'aprobado': 'aprobado', 'no_aprobado': 'no_aprobado'},
    }
    for field, values in options.items():
        if normalized.get(field):
            normalized[field] = values.get(match_key(normalized[field]), normalized[field])
    value = normalized.get('fecha_certificacion', '')
    if value:
        # Slash/hyphen dates are explicitly day/month/year. Numeric CSV dates
        # and timestamp strings remain invalid, rather than becoming 1970.
        for pattern in ('%d/%m/%Y', '%d-%m-%Y'):
            try:
                normalized['fecha_certificacion'] = datetime.strptime(value, pattern).date().isoformat()
                break
            except ValueError:
                pass
    return normalized
