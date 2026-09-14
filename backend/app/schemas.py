import re
from datetime import date
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.services.vigencia import hoy_local

Role = Literal['admin', 'capacitacion', 'trabajador']

class PersonalIn(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    cuip: str | None = Field(None, max_length=20)
    curp: str | None = Field(None, max_length=18)
    nombre_completo: str = Field(min_length=3, max_length=150)
    sexo: Literal['H', 'M'] | None = None
    corporacion_id: UUID
    adscripcion: str = Field(min_length=1, max_length=150)
    cargo_id: UUID | None = None
    grado_id: UUID | None = None
    estatus: Literal['activo', 'baja', 'comisionado', 'licencia'] = 'activo'

    @field_validator('cuip', 'curp', mode='before')
    @classmethod
    def normalize(cls, v):
        return v.strip().upper() or None if isinstance(v, str) else v

    @field_validator('cuip')
    @classmethod
    def check_cuip(cls, v):
        if v and not re.fullmatch(r'[A-Z0-9]{1,20}', v):
            raise ValueError('CUIP: use de 1 a 20 letras o números, sin espacios.')
        return v

    @field_validator('curp')
    @classmethod
    def check_curp(cls, v):
        if v and not re.fullmatch(r'[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[A-Z0-9][0-9]', v):
            raise ValueError('La CURP debe tener 18 caracteres con estructura válida.')
        return v

    @model_validator(mode='after')
    def identifier(self):
        if not self.cuip and not self.curp:
            raise ValueError('Capture CUIP o CURP.')
        return self

class CompetenciaIn(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    personal_id: UUID
    institucion_evaluadora: str = Field(min_length=2, max_length=150)
    fecha_certificacion: date
    resultado: Literal['aprobado', 'no_aprobado']
    folio: str = Field(min_length=1, max_length=60)

    @field_validator('fecha_certificacion')
    @classmethod
    def no_future(cls, v):
        if v > hoy_local():
            raise ValueError('La fecha de certificación no puede ser futura.')
        return v

class DemoSession(BaseModel):
    role: Role
