"""Aba 'Avisos da casa': o que o OuviAí ouviu, transformado em aviso visual.

O celular roda o classificador do Edge Impulse e manda cada detecção para
POST /v1/eventos. Esta tela atualiza sozinha (st.fragment com run_every) sem
recarregar a página inteira, e a pessoa diz se o aviso estava certo.
"""
from datetime import datetime

import streamlit as st

from providers.api import ErroApi, enviar_evento
from state import store
from ui.componentes import CLASSES_SOM, cartao, estado_vazio


def render():
    st.subheader("🔔 Avisos da casa")
    st.caption("O celular escuta a campainha e batidas na porta e avisa aqui, por escrito. "
               "Nenhum áudio é gravado ou enviado: só o tipo de som e a hora.")
    intervalo = 10 if st.session_state.ao_vivo else None
    st.fragment(_avisos, run_every=intervalo)()
    _simulador()


def _hora(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%d/%m %H:%M")


def _avisos():
    try:
        eventos = store.eventos()
    except ErroApi as e:
        st.error(f"⚠️ {e}")
        return
    if not eventos:
        estado_vazio("Nenhum som detectado ainda. Abra o OuviAí no celular para começar.", "🔕")
        return

    alertas = [e for e in eventos if e["alerta"] != "baixa"]
    if alertas:
        u = alertas[0]
        cartao(u["alerta"], u["mensagem"], f"{_hora(u['momento'])} · {u['dispositivo']}",
               f"Certeza do modelo: {u['confianca']:.0%}", grande=True)

    st.markdown("#### Últimos sons")
    for ev in eventos[:8]:
        col_cartao, col_ok, col_erro = st.columns([5, 1.2, 1.2], vertical_alignment="center")
        with col_cartao:
            cartao(ev["alerta"], ev["mensagem"], rodape=f"{_hora(ev['momento'])} · certeza {ev['confianca']:.0%}")
        dado = st.session_state.feedbacks.get(ev["id"], ev["acertou"])
        if dado is None:
            col_ok.button("Certo", key=f"ok{ev['id']}", icon="✔️", help="O aviso estava certo",
                          on_click=_feedback, args=(ev["id"], True))
            col_erro.button("Errado", key=f"erro{ev['id']}", icon="✖️", help="Não era esse som",
                            on_click=_feedback, args=(ev["id"], False))
        else:
            col_ok.markdown("✔️ Certo" if dado else "✖️ Errado")


def _feedback(evento_id: int, acertou: bool):
    try:
        store.registrar_feedback(evento_id, acertou)
    except ErroApi as e:
        st.toast(f"⚠️ {e}")


def _simulador():
    with st.expander("📱 Simular o celular (demonstração)"):
        st.caption("Na casa real, o app do Edge Impulse manda isso sozinho para a API.")
        c1, c2 = st.columns(2)
        classe = c1.selectbox("Som detectado", list(CLASSES_SOM), format_func=CLASSES_SOM.get, key="sim_classe")
        confianca = c2.slider("Certeza do modelo", 0.0, 1.0, 0.9, 0.01, key="sim_conf")
        if st.button("Enviar detecção", icon="📤"):
            try:
                ev = enviar_evento({"momento": datetime.now().isoformat(timespec="seconds"), "classe": classe,
                                    "confianca": confianca, "dispositivo": "celular-demo"})
            except ErroApi as e:
                st.error(f"⚠️ {e}")
                return
            store.eventos.clear()
            store.resumo.clear()
            st.success(f"Recebido: {ev['mensagem']}")
