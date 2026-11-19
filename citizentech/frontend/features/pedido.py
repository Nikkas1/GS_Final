"""Aba 'Pedir ajuda': o cidadão escreve, a IA (no back-end) organiza, o cidadão confirma.

Para quem não ouve, ligar para 156, 135 ou para a UBS não é opção. Aqui o
pedido é por texto e a resposta diz o que fazer sem precisar de telefone.
"""
import streamlit as st

from providers.api import ErroApi, confirmar_pedido
from state import store
from ui.componentes import CATEGORIAS, URGENCIAS, cartao, estado_vazio

EXEMPLOS = [
    "Meu aparelho auditivo parou de funcionar e o posto disse para voltar mês que vem.",
    "Ligaram dizendo que são do INSS e pediram o código que chegou no meu celular.",
    "A calçada na frente da UBS está toda quebrada e minha mãe quase caiu.",
]


def render():
    st.subheader("✍️ Pedir ajuda por escrito")
    if msg := st.session_state.pop("flash", None):
        st.success(msg, icon="✅")
    col_form, col_meus = st.columns([3, 2], gap="large")
    with col_form:
        _formulario()
        if st.session_state.pendente:
            _revisar(st.session_state.pendente)
    with col_meus:
        _meus_pedidos()


def _formulario():
    with st.expander("Não sabe como escrever? Veja exemplos"):
        for ex in EXEMPLOS:
            st.markdown(f"- {ex}")

    with st.form("form_pedido", clear_on_submit=False):
        texto = st.text_area("O que está acontecendo? *", max_chars=1000, height=130,
                             placeholder="Escreva do seu jeito. Não precisa colocar CPF nem telefone.")
        local = st.text_input("Bairro ou endereço (opcional)", max_chars=120)
        foto = st.file_uploader("Foto da calçada ou do muro (opcional)", type=["jpg", "jpeg", "png"],
                                help="Só para problemas na rua. A foto não é guardada.")
        enviado = st.form_submit_button("Enviar pedido", type="primary", icon="📨")

    if not enviado:
        return
    texto, local = texto.strip(), local.strip()
    if len(texto) < 10:
        st.warning("✏️ Escreva um pouco mais (pelo menos 10 letras) para a gente entender.")
        return
    if foto is not None and foto.size > 5 * 1024 * 1024:
        st.warning("🖼️ A foto passa de 5 MB. Envie uma menor ou continue sem foto.")
        return
    _processar(texto, local, foto)


def _processar(texto: str, local: str, foto):
    st.session_state.pendente = None
    with st.status("Lendo seu pedido...", expanded=False) as s:
        try:
            s.update(label="🔒 Escondendo dados pessoais e analisando...")
            resp = store.triagem(texto, local)
        except ErroApi as e:
            s.update(label="Não deu certo", state="error")
            st.error(f"⚠️ {e}")
            return
        visao = None
        if foto is not None:
            s.update(label="🖼️ Olhando a foto...")
            try:
                visao = store.visao(foto.name, foto.getvalue(), foto.type)
            except ErroApi as e:
                st.info(f"A foto não pôde ser analisada ({e}). Seguimos só com o texto.")
        s.update(label="Pronto! Confira abaixo.", state="complete")
    st.session_state.pendente = {"resp": resp, "visao": visao}


def _revisar(pend: dict):
    r, t = pend["resp"], pend["resp"]["triagem"]
    st.markdown("### O que entendemos")
    cartao(t["urgencia"], CATEGORIAS[t["categoria"]].split(" ", 1)[1], t["resumo"], f"Protocolo {r['protocolo']}")
    if r["emergencia"]:
        st.error("🚨 Seu texto fala de uma situação de risco. Se for agora, peça para alguém ligar 192, 193 ou 190.")
    if t["sinais_de_golpe"]:
        st.warning("⚠️ Isso parece golpe. Não passe códigos, senhas nem faça PIX.")
    st.markdown(f"**O que fazer agora:** {t['orientacao']}")
    st.markdown(f"**Quem resolve:** {t['encaminhamento']}")

    v = pend.get("visao")
    if v:
        achado = "possível rachadura" if v["possivel_fissura"] else "nenhuma rachadura aparente"
        st.markdown(f"**Na foto:** {achado} (certeza {v['confianca']:.0%})")
        st.caption(v["aviso"])

    st.divider()
    st.markdown("**Está certo?** A IA pode errar. Corrija se precisar antes de registrar.")
    c1, c2 = st.columns(2)
    cats, urgs = list(CATEGORIAS), list(URGENCIAS)
    categoria = c1.selectbox("Assunto", cats, index=cats.index(t["categoria"]), format_func=CATEGORIAS.get,
                             key=f"cat_{r['id']}")
    urgencia = c2.selectbox("Urgência", urgs, index=urgs.index(t["urgencia"]), format_func=URGENCIAS.get,
                            key=f"urg_{r['id']}")
    util = st.radio("A orientação ajudou?", ["Sim", "Não", "Prefiro não dizer"], index=2, horizontal=True,
                    key=f"util_{r['id']}")

    if st.button("Confirmar e registrar", type="primary", icon="✅", key=f"conf_{r['id']}"):
        try:
            registrado = confirmar_pedido(r["id"], categoria, urgencia, {"Sim": True, "Não": False}.get(util))
        except ErroApi as e:
            st.error(f"⚠️ {e}")
            return
        store.adicionar_meu_pedido(registrado)
        st.session_state.pendente = None
        st.session_state.flash = f"Pedido registrado. Guarde o protocolo: **{registrado['protocolo']}**"
        st.rerun()


def _meus_pedidos():
    st.markdown("#### Meus pedidos")
    meus = st.session_state.meus_pedidos
    if not meus:
        estado_vazio("Os pedidos que você confirmar aparecem aqui.", "📭")
        return
    for p in reversed(meus):
        corrigido = " · você corrigiu a IA" if p["corrigido"] else ""
        cartao(p["urgencia"], CATEGORIAS[p["categoria"]].split(" ", 1)[1], p["resumo"],
               f"{p['protocolo']}{corrigido}")
