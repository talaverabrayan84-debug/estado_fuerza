import base64
import json

import pytest

from app.core.config import Settings


def legacy_key(role):
    payload = base64.urlsafe_b64encode(json.dumps({'role': role}).encode()).decode().rstrip('=')
    return f'header.{payload}.signature'


@pytest.mark.parametrize('key', ['sb_secret_test', legacy_key('service_role')])
def test_production_rejects_privileged_api_keys(key):
    with pytest.raises(RuntimeError, match='pública'):
        Settings(environment='production', demo=False, supabase_url='https://example.supabase.co', supabase_key=key).validate()


@pytest.mark.parametrize('key', ['sb_publishable_test', legacy_key('anon')])
def test_production_accepts_public_key_classes(key):
    Settings(environment='production', demo=False, supabase_url='https://example.supabase.co', supabase_key=key).validate()


def test_vercel_rejects_demo_even_in_development(monkeypatch):
    monkeypatch.setenv('VERCEL', '1')
    with pytest.raises(RuntimeError, match='desarrollo local'):
        Settings(environment='development', demo=True).validate()
