from calendar import monthrange
from datetime import date, datetime
from zoneinfo import ZoneInfo

def hoy_local() -> date:
    return datetime.now(ZoneInfo('America/Mexico_City')).date()

def calcular_vencimiento(fecha: date) -> date:
    year = fecha.year + 3
    return date(year, fecha.month, min(fecha.day, monthrange(year, fecha.month)[1]))

def evaluar_vigencia(fecha: date, hoy: date | None = None, dias_alerta: int = 90) -> str:
    dias = (fecha - (hoy or hoy_local())).days
    return 'Vencida' if dias < 0 else 'Por vencer' if dias <= dias_alerta else 'Vigente'

def detalle_vigencia(registro: dict | None, hoy: date | None = None, dias_alerta: int = 90) -> dict:
    if not registro:
        return {'estatus_vigencia': 'Sin registro', 'dias_restantes': None, 'fecha_vencimiento': None}
    if registro['resultado'] != 'aprobado':
        return {'estatus_vigencia': 'No aprobado', 'dias_restantes': None, 'fecha_vencimiento': None}
    fin = calcular_vencimiento(date.fromisoformat(registro['fecha_certificacion']))
    return {'estatus_vigencia': evaluar_vigencia(fin, hoy, dias_alerta),
            'dias_restantes': (fin - (hoy or hoy_local())).days, 'fecha_vencimiento': fin.isoformat()}
