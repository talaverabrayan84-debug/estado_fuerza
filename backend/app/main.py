from contextlib import asynccontextmanager
from uuid import UUID
from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.security import Context, context, allow, own_or_staff, local_demo, new_demo_session, demo_sessions
from app.schemas import PersonalIn, CompetenciaIn, DemoSession

@asynccontextmanager
async def lifespan(app):
    settings.validate()
    yield

app = FastAPI(title='Estado de Fuerza · Fase 1', version='0.1.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=list(settings.origins),
                   allow_methods=['GET','POST','PUT','DELETE'], allow_headers=['Authorization','Content-Type'])

@app.middleware('http')
async def secure_headers(request, call_next):
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

@app.get('/api/health')
def health(): return {'status': 'ok', 'mode': 'demo' if settings.demo else 'supabase'}

@app.post('/api/demo/session')
def demo_login(data: DemoSession, request: Request):
    local_demo(request)
    return {'access_token': new_demo_session(data.role)}

@app.delete('/api/demo/session', status_code=204)
def demo_logout(request: Request, ctx: Context = Depends(context)):
    local_demo(request)
    demo_sessions.pop(request.headers.get('authorization','').removeprefix('Bearer '), None)

@app.get('/api/me')
def me(ctx: Context = Depends(context)): return ctx.user

@app.get('/api/catalogos')
def catalogs(ctx: Context = Depends(context)): return ctx.repo.catalogs()

@app.get('/api/configuracion')
def config(ctx: Context = Depends(context)): return ctx.repo.config()

@app.get('/api/personal')
def personal(q: str = Query('', max_length=150), estatus: str = '', corporacion_id: UUID | None = None,
             vigencia: str = '', offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
             ctx: Context = Depends(context)):
    allow(ctx, 'admin', 'capacitacion')
    rows = ctx.repo.list_personal(q=q.strip(), estatus=estatus, corporacion_id=str(corporacion_id) if corporacion_id else '',
                                  vigencia=vigencia, offset=offset, limit=limit+1)
    return {'items': rows[:limit], 'has_more': len(rows)>limit, 'offset': offset, 'limit': limit}

@app.get('/api/personal/{person_id}')
def person(person_id: UUID, ctx: Context = Depends(context)):
    own_or_staff(ctx, person_id)
    return ctx.repo.get_personal(str(person_id))

@app.post('/api/personal', status_code=201)
def add_person(data: PersonalIn, ctx: Context = Depends(context)):
    allow(ctx, 'admin')
    return ctx.repo.save_personal(data.model_dump(mode='json'))

@app.put('/api/personal/{person_id}')
def update_person(person_id: UUID, data: PersonalIn, ctx: Context = Depends(context)):
    allow(ctx, 'admin')
    return ctx.repo.save_personal(data.model_dump(mode='json'), str(person_id))

@app.get('/api/competencias-basicas/{person_id}')
def history(person_id: UUID, ctx: Context = Depends(context)):
    own_or_staff(ctx, person_id)
    ctx.repo.get_personal(str(person_id))
    return ctx.repo.history(str(person_id))

@app.post('/api/competencias-basicas', status_code=201)
def add_competencia(data: CompetenciaIn, ctx: Context = Depends(context)):
    allow(ctx, 'admin', 'capacitacion')
    return ctx.repo.add_competencia(data.model_dump(mode='json'))

@app.get('/api/alertas/resumen')
def summary(ctx: Context = Depends(context)):
    allow(ctx, 'admin', 'capacitacion')
    return ctx.repo.summary()
