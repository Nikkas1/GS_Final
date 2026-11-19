"""Cliente HTTP da API. Único lugar do front que conhece URLs e status HTTP.

Toda falha técnica vira ErroApi com uma mensagem pronta para o cidadão.
O front nunca fala com o provedor de IA: só com a nossa API FastAPI.
"""
import os

import requests
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())
API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
TIMEOUT_IA = 45     # a triagem passa pelo LLM
TIMEOUT_RAPIDO = 8  # listas e confirmações

_sessao = requests.Session()   # reaproveita conexões TCP entre chamadas


class ErroApi(Exception):
    """A mensagem já está pronta para ser mostrada ao cidadão."""


MENSAGENS = {
    404: "Não encontramos esse registro. Atualize a página.",
    413: "Imagem muito grande. Envie um arquivo de até 5 MB.",
    415: "Formato de imagem não aceito. Envie JPG ou PNG.",
    422: "Confira os campos: o pedido precisa ter pelo menos 10 caracteres.",
    502: "O assistente não conseguiu entender a resposta agora. Tente de novo.",
    503: "O assistente está indisponível no momento. Seu texto não foi perdido: tente em alguns minutos.",
    504: "A análise demorou mais que o esperado. Tente de novo.",
}


def _req(metodo: str, caminho: str, timeout: int, **kwargs):
    try:
        r = _sessao.request(metodo, f"{API_URL}{caminho}", timeout=timeout, **kwargs)
    except requests.exceptions.ConnectionError:
        raise ErroApi("O serviço está fora do ar no momento. Tente novamente em alguns minutos.")
    except requests.exceptions.Timeout:
        raise ErroApi(MENSAGENS[504])
    if r.status_code >= 400:
        raise ErroApi(MENSAGENS.get(r.status_code, "Não conseguimos concluir agora. Tente novamente."))
    try:
        return r.json()
    except ValueError:
        raise ErroApi("Recebemos uma resposta inesperada. Tente novamente.")


def _exigir(dados, *chaves):
    """Resposta inválida (faltando campo) também é tratada, não vira KeyError na tela."""
    if not isinstance(dados, dict) or any(c not in dados for c in chaves):
        raise ErroApi("Recebemos uma resposta inesperada. Tente novamente.")
    return dados


# ---------- saúde ----------
def status_api() -> dict | None:
    try:
        return _req("GET", "/health/ready", 3)
    except ErroApi:
        return None


# ---------- pedidos ----------
def triar_pedido(texto: str, local: str) -> dict:
    d = _req("POST", "/v1/pedidos", TIMEOUT_IA, json={"texto": texto, "local": local})
    _exigir(d, "id", "protocolo", "triagem", "emergencia")
    _exigir(d["triagem"], "categoria", "urgencia", "resumo", "orientacao", "encaminhamento", "sinais_de_golpe")
    return d


def confirmar_pedido(pedido_id: int, categoria: str, urgencia: str, util: bool | None) -> dict:
    d = _req("POST", f"/v1/pedidos/{pedido_id}/confirmacao", TIMEOUT_RAPIDO,
             json={"categoria": categoria, "urgencia": urgencia, "util": util})
    return _exigir(d, "protocolo", "categoria", "urgencia")


def listar_pedidos() -> list[dict]:
    d = _req("GET", "/v1/pedidos", TIMEOUT_RAPIDO)
    if not isinstance(d, list):
        raise ErroApi("Recebemos uma resposta inesperada. Tente novamente.")
    return d


# ---------- eventos OuviAí ----------
def listar_eventos(limite: int = 500) -> list[dict]:
    d = _req("GET", "/v1/eventos", TIMEOUT_RAPIDO, params={"limite": limite})
    if not isinstance(d, list):
        raise ErroApi("Recebemos uma resposta inesperada. Tente novamente.")
    return d


def enviar_evento(evento: dict) -> dict:
    d = _req("POST", "/v1/eventos", TIMEOUT_RAPIDO, json=[evento])
    return _exigir(d[0] if isinstance(d, list) and d else None, "id", "alerta", "mensagem")


def feedback_evento(evento_id: int, acertou: bool) -> dict:
    return _req("PATCH", f"/v1/eventos/{evento_id}/feedback", TIMEOUT_RAPIDO, json={"acertou": acertou})


# ---------- painel e visão ----------
def resumo() -> dict:
    return _req("GET", "/v1/painel/resumo", TIMEOUT_RAPIDO)


def classificar_foto(nome: str, conteudo: bytes, tipo: str) -> dict:
    d = _req("POST", "/v1/visao/classificar", TIMEOUT_IA, files={"arquivo": (nome, conteudo, tipo)})
    return _exigir(d, "possivel_fissura", "confianca", "aviso")
