from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.services.vigencia import hoy_local
from app.services.calendar_dates import CalendarDate

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class CursoIn(Input):
    nombre_curso: str = Field(min_length=3, max_length=200)
    tipo: Literal['formacion_inicial', 'competencias_basicas', 'actualizacion', 'especialidad']
    fuente_financiamiento: Literal['FASP', 'FOFISP', 'recurso_propio', 'otro']
    institucion_impartidora: str = Field(min_length=2, max_length=150)
    horas: int = Field(ge=1, le=10000)
    vigencia_meses: int | None = Field(None, ge=1, le=120)

    @model_validator(mode='after')
    def fixed_validity(self):
        if self.tipo == 'competencias_basicas':
            self.vigencia_meses = 36
        return self

class SesionIn(Input):
    curso_id: UUID
    fecha_inicio: CalendarDate
    fecha_fin: CalendarDate
    sede: str = Field(min_length=2, max_length=150)
    modalidad: Literal['presencial', 'en_linea', 'mixta']
    cupo: int = Field(ge=1, le=10000)

    @model_validator(mode='after')
    def dates(self):
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError('La fecha de término debe ser igual o posterior al inicio.')
        if (self.fecha_fin - self.fecha_inicio).days > 1096:
            raise ValueError('La sesión no puede abarcar más de tres años.')
        return self

class InscripcionIn(Input):
    personal_id: UUID
    estatus: Literal['inscrito', 'en_curso', 'concluido', 'baja'] = 'inscrito'
    calificacion: Decimal | None = Field(None, ge=0, le=100, decimal_places=2)

class BitacoraIn(Input):
    sesion_id: UUID | None = None
    fecha: CalendarDate
    tipo_actividad: Literal['avance', 'incidencia', 'entrega', 'observacion']
    descripcion: str = Field(min_length=3, max_length=5000)

    @field_validator('fecha')
    @classmethod
    def no_future(cls, v):
        if v > hoy_local():
            raise ValueError('La fecha de la bitácora no puede ser futura.')
        return v
