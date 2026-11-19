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


def test_tool_use_forcado_com_schema_do_pydantic():
    corpo = {"id": "msg_1", "type": "message", "role": "assistant", "model": "m", "stop_reason": "tool_use",
             "content": [{"type": "tool_use", "id": "t1", "name": "registrar_triagem", "input": TRIAGEM}],
             "usage": {"input_tokens": 1, "output_tokens": 1}}
    t, enviado = transporte(corpo=corpo)
    llm = AnthropicLLM("chave-falsa", "claude-sonnet-5-5", 5, http_client=httpx.AsyncClient(transport=t))
    assert asyncio.run(llm.estruturar("sys", "pedido", TriagemIA)) == TRIAGEM
    assert enviado["tool_choice"] == {"type": "tool", "name": "registrar_triagem"}
    assert "$defs" not in json.dumps(enviado["tools"][0]["input_schema"])


def test_chave_recusada():
    t, _ = transporte(401, {"type": "error", "error": {"type": "authentication_error", "message": "x"}})
    llm = AnthropicLLM("chave-errada", "m", 5, http_client=httpx.AsyncClient(transport=t))
    with pytest.raises(ProvedorIndisponivel):
        asyncio.run(llm.estruturar("s", "u", TriagemIA))


def test_sem_chave():
    with pytest.raises(ProvedorIndisponivel):
        asyncio.run(AnthropicLLM("", "m", 5).estruturar("s", "u", TriagemIA))
