"""O provedor real, sem internet: o HTTP do SDK da Anthropic é respondido por um transporte falso."""
import asyncio
import json

import httpx2 as httpx
import pytest

from providers.llm import AnthropicLLM, ProvedorIndisponivel
from schemas.pedido import TriagemIA

TRIAGEM = {"categoria": "transporte", "urgencia": "baixa", "resumo": "Bilhete especial.",
           "orientacao": "Vá à SPTrans com o laudo.", "encaminhamento": "SPTrans", "sinais_de_golpe": False}


def transporte(status=200, corpo=None):
    enviado = {}

    def responder(request: httpx.Request):
        enviado.update(json.loads(request.content))
        return httpx.Response(status, json=corpo)
    return httpx.MockTransport(responder), enviado


def test_saida_estruturada_com_schema_do_pydantic():
    corpo = {"id": "msg_1", "type": "message", "role": "assistant", "model": "m", "stop_reason": "end_turn",
             "content": [{"type": "text", "text": json.dumps(TRIAGEM)}],
             "usage": {"input_tokens": 1, "output_tokens": 1}}
    t, enviado = transporte(corpo=corpo)
    llm = AnthropicLLM("chave-falsa", "claude-sonnet-5-5", 5, http_client=httpx.AsyncClient(transport=t))
    assert asyncio.run(llm.estruturar("sys", "pedido", TriagemIA)) == TRIAGEM
    fmt = enviado["output_config"]["format"]
    assert fmt["type"] == "json_schema" and "tools" not in enviado
    texto = json.dumps(fmt["schema"])
    assert "$defs" not in texto and "maxLength" not in texto
    assert fmt["schema"]["additionalProperties"] is False
    assert set(fmt["schema"]["required"]) == set(TRIAGEM)


def test_chave_recusada():
    t, _ = transporte(401, {"type": "error", "error": {"type": "authentication_error", "message": "x"}})
    llm = AnthropicLLM("chave-errada", "m", 5, http_client=httpx.AsyncClient(transport=t))
    with pytest.raises(ProvedorIndisponivel):
        asyncio.run(llm.estruturar("s", "u", TriagemIA))


def test_sem_chave():
    with pytest.raises(ProvedorIndisponivel):
        asyncio.run(AnthropicLLM("", "m", 5).estruturar("s", "u", TriagemIA))
