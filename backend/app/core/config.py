import base64
import json
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()
project_url = os.getenv('SUPABASE_PROJECT_URL', '').strip()

@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv('APP_ENV', 'production')
    demo: bool = os.getenv('DEMO_MODE', 'false').lower() == 'true'
    supabase_url: str = (project_url or os.getenv('SUPABASE_URL', '')).rstrip('/')
    supabase_key: str = os.getenv('SUPABASE_PUBLISHABLE_KEY', '') if project_url else os.getenv('SUPABASE_ANON_KEY', '')
    origins: tuple = tuple(os.getenv('FRONTEND_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(','))

    def validate(self):
        if self.demo and (self.environment != 'development' or os.getenv('VERCEL')):
            raise RuntimeError('La demostración solo está permitida en desarrollo local.')
        if not self.demo and (not self.supabase_url.startswith('https://') or not self.supabase_key):
            raise RuntimeError('Configure SUPABASE_URL y SUPABASE_ANON_KEY antes de iniciar.')
        # This inspects the key class only, never authenticates a JWT. User JWTs
        # are validated by Supabase Auth. Reject accidental privileged API keys.
        if not self.demo:
            privileged = self.supabase_key.startswith('sb_secret_')
            parts = self.supabase_key.split('.')
            if len(parts) == 3:
                try:
                    payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=' * (-len(parts[1]) % 4)))
                    privileged = privileged or (isinstance(payload, dict) and payload.get('role') == 'service_role')
                except (ValueError, UnicodeError):
                    pass
            if privileged:
                raise RuntimeError('Use exclusivamente la clave pública anon o publishable de Supabase.')

settings = Settings()
