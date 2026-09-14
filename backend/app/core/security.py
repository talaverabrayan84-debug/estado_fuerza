from dataclasses import dataclass
from secrets import token_urlsafe
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import settings
from app.db.supabase_client import SupabaseRepository

bearer = HTTPBearer(auto_error=False)
demo_sessions: dict = {}

@dataclass
class Context:
    user: dict
    repo: object

def local_demo(request: Request):
    if not settings.demo or not request.client or request.client.host not in ('127.0.0.1','::1','localhost','testclient'):
        raise HTTPException(404, 'Recurso no disponible.')

def new_demo_session(role):
    from app.db.demo import WORKER_ID
    token = token_urlsafe(32)
    demo_sessions[token] = {'id': 'demo-' + role, 'rol': role, 'activo': True,
                           'personal_id': WORKER_ID if role == 'trabajador' else None,
                           'email': f'{role}@demostracion.local'}
    return token

def context(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not credentials: raise HTTPException(401, 'Inicie sesión para continuar.')
    token = credentials.credentials
    if settings.demo:
        local_demo(request)
        from app.db.demo import DemoRepository, store
        user = demo_sessions.get(token)
        if not user: raise HTTPException(401, 'Sesión de demostración no válida.')
        return Context(user, DemoRepository(store, user))
    repo = SupabaseRepository(token)
    return Context(repo.profile(), repo)

def allow(ctx, *roles):
    if ctx.user['rol'] not in roles: raise HTTPException(403, 'Su rol no permite esta operación.')

def own_or_staff(ctx, person_id):
    if ctx.user['rol'] == 'trabajador' and str(person_id) != ctx.user['personal_id']:
        raise HTTPException(404, 'Expediente no encontrado.')
