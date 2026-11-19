from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from core.deps import LLMDep, RepoDep
from pipelines.triagem import RespostaInvalida, novo_protocolo, triar
from providers.llm import ProvedorIndisponivel, TempoEsgotado
from schemas.pedido import Categoria, Confirmacao, PedidoEntrada, PedidoRegistrado, PedidoTriado, Urgencia

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


def _registrado(p: dict) -> PedidoRegistrado:
    t = p["triagem"]
    cat, urg = p["categoria"] or t["categoria"], p["urgencia"] or t["urgencia"]
    return PedidoRegistrado(
        id=p["id"], protocolo=p["protocolo"], criado_em=p["criado_em"], local=p["local"], resumo=t["resumo"],
        categoria=cat, urgencia=urg, categoria_ia=t["categoria"], urgencia_ia=t["urgencia"],
        corrigido=(cat, urg) != (t["categoria"], t["urgencia"]), util=p["util"], status=p["status"],
    )


@router.post("", response_model=PedidoTriado, status_code=status.HTTP_201_CREATED,
             summary="Envia um pedido para a triagem da IA",
             responses={502: {"description": "IA respondeu fora do formato"},
                        503: {"description": "IA indisponível"}, 504: {"description": "IA demorou demais"}})
async def criar_pedido(entrada: PedidoEntrada, repo: RepoDep, llm: LLMDep):
    try:
        texto, triagem, emergencia = await triar(entrada, llm)
    except TempoEsgotado:
        raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, "A análise demorou mais que o esperado.")
    except ProvedorIndisponivel:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "O assistente está indisponível no momento.")
    except RespostaInvalida:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Não foi possível analisar o pedido agora.")
    # ErroProvedor genérico cai no handler global (main.py) e vira 502 sem detalhe técnico

    p = repo.criar_pedido(novo_protocolo(), texto, entrada.local.strip(), triagem.model_dump(mode="json"), emergencia)
    return PedidoTriado(**{**p, "triagem": triagem})


@router.post("/{pedido_id}/confirmacao", response_model=PedidoRegistrado,
             summary="Human-in-the-loop: confirma ou corrige a triagem")
def confirmar(pedido_id: int, conf: Confirmacao, repo: RepoDep):
    if repo.obter_pedido(pedido_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado.")
    p = repo.confirmar_pedido(pedido_id, conf.categoria.value, conf.urgencia.value, conf.util)
    return _registrado(p)


@router.get("", response_model=list[PedidoRegistrado], summary="Pedidos confirmados (com filtros)")
def listar(repo: RepoDep,
           categoria: Annotated[list[Categoria] | None, Query()] = None,
           urgencia: Annotated[list[Urgencia] | None, Query()] = None):
    cats = [c.value for c in categoria] if categoria else None
    urgs = [u.value for u in urgencia] if urgencia else None
    return [_registrado(p) for p in repo.listar_pedidos(cats, urgs)]
