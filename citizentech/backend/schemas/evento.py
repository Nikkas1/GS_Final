"""Evento sonoro do OuviAí, no formato `evento_som` do contrato de integração (v1.0.0)."""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ClasseSom(str, Enum):
    campainha = "campainha"
    batida_porta = "batida_porta"
    ambiente = "ambiente"


class NivelAlerta(str, Enum):
    alta = "alta"      # alguém na porta de madrugada, ou som repetido
    media = "media"    # alguém na porta
    baixa = "baixa"    # som ambiente ou detecção incerta


class EventoSom(BaseModel):
    momento: datetime
    classe: ClasseSom
    confianca: float = Field(ge=0, le=1, description="0 a 1, não percentual")
    dispositivo: str = Field(min_length=1, max_length=40, pattern=r"^[\w\-]+$",
                             description="Apelido do celular, sem nome real nem telefone")


class EventoRegistrado(EventoSom):
    id: int
    alerta: NivelAlerta
    mensagem: str = Field(description="Aviso em texto simples para a pessoa surda")
    incerto: bool
    acertou: bool | None = Field(description="Feedback humano: o aviso estava certo?")


class Feedback(BaseModel):
    acertou: bool
