"""Bound upload transport before multipart parsing can spool unlimited data."""
from starlette.formparsers import MultiPartException
from starlette.responses import JSONResponse

MAX_UPLOAD_BODY = 3 * 1024 * 1024  # 2 MB file plus multipart fields and headers.


class UploadBodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '').rstrip('/')
        upload = path == '/api/carga-masiva/previsualizar' or (
            path.startswith('/api/bitacora/') and path.endswith('/evidencia'))
        if scope['type'] != 'http' or scope.get('method') != 'POST' or not upload:
            return await self.app(scope, receive, send)

        rejected = JSONResponse({'detail': 'La solicitud de carga excede el máximo de 3 MB.'}, status_code=413)
        for key, value in scope.get('headers', []):
            if key.lower() == b'content-length':
                try:
                    if int(value) > MAX_UPLOAD_BODY:
                        return await rejected(scope, receive, send)
                except ValueError:
                    pass  # The byte counter remains authoritative.

        size = 0
        exceeded = False

        async def bounded_receive():
            nonlocal size, exceeded
            message = await receive()
            if message['type'] == 'http.request':
                size += len(message.get('body', b''))
                if size > MAX_UPLOAD_BODY:
                    exceeded = True
                    # Starlette catches this exception and closes spooled files.
                    raise MultiPartException('El cuerpo de carga excede el límite.')
            return message

        async def bounded_send(message):
            if not exceeded:
                await send(message)

        await self.app(scope, bounded_receive, bounded_send)
        if exceeded:
            # Replace the multipart parser's 400 with the transport limit status.
            await rejected(scope, receive, send)
