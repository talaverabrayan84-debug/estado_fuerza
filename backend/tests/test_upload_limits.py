import asyncio
from starlette import formparsers
from app.main import app
from app.core.upload_limits import MAX_UPLOAD_BODY


def test_oversized_anonymous_upload_rejected_before_spooling(client, monkeypatch):
    def unexpected_spool(*args, **kwargs):
        raise AssertionError('Content-Length must be rejected before multipart parsing')

    monkeypatch.setattr(formparsers, 'SpooledTemporaryFile', unexpected_spool)
    for path in ['/api/carga-masiva/previsualizar',
                 '/api/bitacora/20000000-0000-0000-0000-000000000001/evidencia']:
        response = client.post(path, files={'archivo': ('large.csv', b'x' * MAX_UPLOAD_BODY)})
        assert response.status_code == 413


def test_chunked_anonymous_upload_is_bounded_and_closes_tempfile(monkeypatch):
    files = []
    original = formparsers.SpooledTemporaryFile

    def track_spool(*args, **kwargs):
        file = original(*args, **kwargs)
        files.append(file)
        return file

    monkeypatch.setattr(formparsers, 'SpooledTemporaryFile', track_spool)
    preamble = b'--test\r\nContent-Disposition: form-data; name="archivo"; filename="huge.csv"\r\nContent-Type: text/csv\r\n\r\n'
    chunks = iter([preamble] + [b'x' * 65536] * 50 + [b'\r\n--test--\r\n'])
    consumed = 0
    messages = []

    async def receive():
        nonlocal consumed
        consumed += 1
        return {'type': 'http.request', 'body': next(chunks), 'more_body': True}

    async def send(message):
        messages.append(message)

    scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
             'method': 'POST', 'scheme': 'http', 'path': '/api/carga-masiva/previsualizar',
             'raw_path': b'/api/carga-masiva/previsualizar', 'root_path': '', 'query_string': b'',
             'headers': [(b'content-type', b'multipart/form-data; boundary=test')],
             'client': ('127.0.0.1', 12345), 'server': ('testserver', 80)}
    asyncio.run(app(scope, receive, send))
    assert next(m for m in messages if m['type'] == 'http.response.start')['status'] == 413
    assert consumed < 51  # Stop before receiving the remainder of the upload.
    assert files and all(file.closed for file in files)
