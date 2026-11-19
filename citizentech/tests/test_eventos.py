from datetime import datetime

from pipelines.eventos import classificar
from schemas.evento import EventoSom


def ev(classe, conf, hora=15):
    return EventoSom(momento=datetime(2026, 11, 2, hora, 0), classe=classe, confianca=conf, dispositivo="cel-teste")


def test_campainha_de_dia_e_atencao():
    assert classificar(ev("campainha", 0.9), 0.6, 0)["alerta"] == "media"


def test_batida_de_madrugada_e_urgente():
    r = classificar(ev("batida_porta", 0.8, hora=2), 0.6, 0)
    assert r["alerta"] == "alta" and "madrugada" in r["mensagem"]


def test_repeticao_vira_urgente():
    assert classificar(ev("campainha", 0.9), 0.6, 2)["alerta"] == "alta"


def test_confianca_baixa_e_incerto_sem_alerta():
    r = classificar(ev("campainha", 0.4), 0.6, 0)
    assert r["incerto"] and r["alerta"] == "baixa"


def test_ambiente_nao_gera_alerta():
    assert classificar(ev("ambiente", 0.99, hora=3), 0.6, 0)["alerta"] == "baixa"
