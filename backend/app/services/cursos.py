from datetime import date
from app.services.vigencia import hoy_local

def estatus_sesion(inicio: str, fin: str, hoy: date | None = None) -> str:
    hoy = hoy or hoy_local()
    if hoy < date.fromisoformat(inicio):
        return 'Próximo'
    return 'Concluido' if hoy > date.fromisoformat(fin) else 'En curso'
