import asyncio

import pytest

from conftest import LLMFalso
from pipelines.triagem import RespostaInvalida, tem_emergencia, triar
from providers.llm import TempoEsgotado
from schemas.pedido import PedidoEntrada

OK = {"categoria": "saude_auditiva", "urgencia": "media", "resumo": "Aparelho auditivo quebrado.",
      "orientacao": "Procure a UBS.", "encaminhamento": "UBS", "sinais_de_golpe": False}


def rodar(entrada, llm):
    return asyncio.run(triar(entrada, llm))


def test_resposta_valida():
    _, t, emerg = rodar(PedidoEntrada(texto="Meu aparelho auditivo parou de funcionar"), LLMFalso(OK))
    assert t.categoria.value == "saude_auditiva" and not emerg


def test_dados_pessoais_mascarados_antes_do_llm():
    llm = LLMFalso(OK)
    texto, _, _ = rodar(PedidoEntrada(texto="meu cpf é 123.456.789-00 e o tel (11) 98765-4321"), llm)
    assert "123.456" not in llm.recebido[0] and "98765" not in llm.recebido[0]
    assert "[CPF]" in texto and "[TELEFONE]" in texto


def test_texto_longo_e_cortado_e_nao_vira_erro():
    longo = {**OK, "resumo": "x" * 260}
    _, t, _ = rodar(PedidoEntrada(texto="Meu aparelho auditivo parou"), LLMFalso(longo))
    assert len(t.resumo) == 200


def test_fora_do_schema_tenta_de_novo():
    _, t, _ = rodar(PedidoEntrada(texto="Meu aparelho auditivo parou"), LLMFalso({**OK, "categoria": "dragao"}, OK))
    assert t.categoria.value == "saude_auditiva"


def test_fora_do_schema_duas_vezes():
    ruim = {**OK, "urgencia": "altissima"}
    with pytest.raises(RespostaInvalida):
        rodar(PedidoEntrada(texto="Meu aparelho auditivo parou"), LLMFalso(ruim, ruim))


def test_emergencia_forca_urgencia_alta_mesmo_se_a_ia_errar():
    _, t, emerg = rodar(PedidoEntrada(texto="Socorro, caí no chão e não consigo levantar"), LLMFalso({**OK, "urgencia": "baixa"}))
    assert emerg and t.urgencia.value == "alta" and "192" in t.orientacao


def test_falha_do_provedor_sobe():
    with pytest.raises(TempoEsgotado):
        rodar(PedidoEntrada(texto="Meu aparelho auditivo parou"), LLMFalso(TempoEsgotado("lento")))


@pytest.mark.parametrize("texto", ["tem CHEIRO DE GÁS aqui", "alguém está forçando a porta"])
def test_palavras_de_emergencia_sem_acento(texto):
    assert tem_emergencia(texto)
