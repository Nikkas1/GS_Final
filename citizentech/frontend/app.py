"""OuviAí Cidade · CitizenTech — interface Streamlit.

streamlit run app.py   (a API precisa estar no ar em API_URL)
"""
import streamlit as st

from features import avisos, painel, pedido
from state import store
from ui.componentes import aplicar_tema

st.set_page_config(page_title="OuviAí Cidade", page_icon="👂", layout="wide")
store.init_state()
aplicar_tema()

with st.sidebar:
    st.title("👂 OuviAí Cidade")
    st.write("Para quem não ouve bem: a casa avisa por escrito quando alguém chama na porta, "
             "e você pede ajuda sem precisar telefonar.")

    st.toggle("Alto contraste", key="alto_contraste")
    st.toggle("Atualizar avisos sozinho", key="ao_vivo", help="Busca sons novos a cada 10 segundos")

    status = store.status_api()
    if status is None:
        st.error("🔴 Serviço fora do ar")
    elif status["llm"] == "sem_chave":
        st.warning("🟠 Assistente sem chave de IA: os avisos funcionam, os pedidos não.")
    else:
        modo = " (modo demonstração)" if status["llm"] == "simulado" else ""
        st.success(f"🟢 Serviço no ar{modo}")

    st.caption("A IA ajuda a organizar, mas pode errar: você sempre confere antes de registrar. "
               "Não guardamos áudio, e CPF, telefone e e-mail são escondidos antes da análise.")

aba_avisos, aba_pedido, aba_painel = st.tabs(["🔔 Avisos da casa", "✍️ Pedir ajuda", "📊 Painel"])
with aba_avisos:
    avisos.render()
with aba_pedido:
    pedido.render()
with aba_painel:
    painel.render()
