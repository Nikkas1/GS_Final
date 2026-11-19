"""Transforma a detecção do classificador de áudio (Edge Impulse) num aviso visual.

Mesmas regras do Robô Cuidador (RPA/config/regras.json): confiança mínima 0,60,
madrugada entre 22h e 6h, e o mesmo som 3 vezes em 3 minutos vira alerta alto.
"""
from datetime import timedelta

from schemas.evento import EventoSom

MENSAGENS = {
    "campainha": "🔔 Tocaram a campainha",
    "batida_porta": "🚪 Bateram na porta",
    "ambiente": "🔈 Barulho comum na casa",
}
JANELA_REPETICAO = timedelta(minutes=3)
REPETICOES_ALERTA = 3


def noturno(hora: int) -> bool:
    return hora >= 22 or hora < 6


def classificar(evento: EventoSom, confianca_minima: float, repeticoes_recentes: int) -> dict:
    """repeticoes_recentes = quantos eventos iguais do mesmo celular já existem na janela."""
    incerto = evento.confianca < confianca_minima
    classe = evento.classe.value
    mensagem = MENSAGENS[classe]

    if incerto:
        alerta, mensagem = "baixa", f"{mensagem}? (não tenho certeza, confira)"
    elif classe == "ambiente":
        alerta = "baixa"
    elif noturno(evento.momento.hour) or repeticoes_recentes + 1 >= REPETICOES_ALERTA:
        alerta = "alta"
        motivo = "de madrugada" if noturno(evento.momento.hour) else "várias vezes seguidas"
        mensagem = f"{mensagem} {motivo}. Veja quem é antes de abrir."
    else:
        alerta = "media"

    return {**evento.model_dump(), "alerta": alerta, "mensagem": mensagem, "incerto": incerto}
