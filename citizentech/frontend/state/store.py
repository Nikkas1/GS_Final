"""Estado centralizado (st.session_state) e leituras em cache da API.

- session_state: o que é da sessão do cidadão (meus pedidos, pedido aguardando
  revisão, preferências de acessibilidade).
- st.cache_data: leituras da API com TTL curto. Cada rerun do Streamlit
  (clicar num filtro, por exemplo) NÃO chama a API de novo; depois de gravar
  algo, limpamos o cache certo com .clear().
"""
import streamlit as st

from providers import api


def init_state():
    st.session_state.setdefault("meus_pedidos", [])     # pedidos confirmados nesta sessão
    st.session_state.setdefault("pendente", None)       # triagem da IA aguardando o cidadão
    st.session_state.setdefault("alto_contraste", False)
    st.session_state.setdefault("ao_vivo", True)        # atualizar avisos sozinho
    st.session_state.setdefault("feedbacks", {})        # evento_id -> acertou (evita clicar 2x)


def adicionar_meu_pedido(pedido: dict):
    st.session_state.meus_pedidos.append(pedido)
    pedidos.clear()
    resumo.clear()


def registrar_feedback(evento_id: int, acertou: bool):
    api.feedback_evento(evento_id, acertou)
    st.session_state.feedbacks[evento_id] = acertou
    eventos.clear()
    resumo.clear()


# ---------- leituras em cache ----------
@st.cache_data(ttl=10, show_spinner=False)
def eventos() -> list[dict]:
    return api.listar_eventos()


@st.cache_data(ttl=30, show_spinner=False)
def pedidos() -> list[dict]:
    return api.listar_pedidos()


@st.cache_data(ttl=15, show_spinner=False)
def resumo() -> dict:
    return api.resumo()


@st.cache_data(ttl=30, show_spinner=False)
def status_api() -> dict | None:
    return api.status_api()


@st.cache_data(ttl=600, show_spinner=False, max_entries=100)
def triagem(texto: str, local: str) -> dict:
    """O mesmo texto não vai ao LLM duas vezes em 10 minutos (duplo clique, rerun)."""
    return api.triar_pedido(texto, local)


@st.cache_data(ttl=600, show_spinner=False, max_entries=20)
def visao(nome: str, conteudo: bytes, tipo: str) -> dict:
    return api.classificar_foto(nome, conteudo, tipo)
