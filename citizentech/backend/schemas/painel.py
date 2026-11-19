from pydantic import BaseModel


class Resumo(BaseModel):
    pedidos_confirmados: int
    pedidos_alta: int
    taxa_correcao: float | None   # % de triagens que o cidadão corrigiu
    taxa_util: float | None       # % de orientações marcadas como úteis
    eventos_total: int
    eventos_alerta: int
    acerto_eventos: float | None  # entre os eventos com feedback
