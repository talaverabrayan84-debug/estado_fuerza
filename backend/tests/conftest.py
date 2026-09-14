import os
os.environ['APP_ENV'] = 'development'
os.environ['DEMO_MODE'] = 'true'
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import demo
from app.core.security import demo_sessions

@pytest.fixture
def client():
    demo.store = demo.DemoStore()
    demo_sessions.clear()
    with TestClient(app) as client:
        yield client

@pytest.fixture
def auth(client):
    def login(role='admin'):
        token = client.post('/api/demo/session', json={'role': role}).json()['access_token']
        return {'Authorization': f'Bearer {token}'}
    return login
