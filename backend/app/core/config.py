import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv('APP_ENV', 'production')
    demo: bool = os.getenv('DEMO_MODE', 'false').lower() == 'true'
    supabase_url: str = os.getenv('SUPABASE_URL', '').rstrip('/')
    supabase_key: str = os.getenv('SUPABASE_ANON_KEY', '')
    origins: tuple = tuple(os.getenv('FRONTEND_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(','))

    def validate(self):
        if self.demo and (self.environment != 'development' or os.getenv('VERCEL')):
            raise RuntimeError('La demostración solo está permitida en desarrollo local.')
        if not self.demo and (not self.supabase_url.startswith('https://') or not self.supabase_key):
            raise RuntimeError('Configure SUPABASE_URL y SUPABASE_ANON_KEY antes de iniciar.')

settings = Settings()
