"""Aba 'Painel': visão do cuidador / gestor, com Plotly e filtros."""
import pandas as pd
import plotly.express as px
import streamlit as st

from providers.api import ErroApi
from state import store
from ui.componentes import CATEGORIAS, CLASSES_SOM, CORES_ROTULO, URGENCIAS, estado_vazio, porcentagem


def render():
    st.subheader("📊 Painel do cuidador")
    try:
        r = store.resumo()
        eventos = store.eventos()
        pedidos = store.pedidos()
    except ErroApi as e:
        st.error(f"⚠️ {e}")
        return

    m = st.columns(4)
    m[0].metric("Avisos de porta", r["eventos_alerta"], help="Campainha ou batida com certeza ≥ 60%")
    m[1].metric("Acerto dos avisos", porcentagem(r["acerto_eventos"]), help="Entre os avisos marcados como certo/errado")
    m[2].metric("Pedidos registrados", r["pedidos_confirmados"])
    m[3].metric("IA corrigida pelo cidadão", porcentagem(r["taxa_correcao"]),
                help="Quanto maior, mais a IA está errando a triagem")

    aba_sons, aba_pedidos = st.tabs(["🔔 Sons da casa", "✍️ Pedidos"])
    with aba_sons:
        _sons(eventos)
    with aba_pedidos:
        _pedidos(pedidos)


def _sons(eventos: list[dict]):
    if not eventos:
        estado_vazio("Sem sons registrados.", "🔕")
        return
    df = pd.DataFrame(eventos)
    df["momento"] = pd.to_datetime(df["momento"])
    df["som"] = df["classe"].map(CLASSES_SOM)
    df["aviso"] = df["alerta"].map(URGENCIAS)

    c1, c2, c3 = st.columns([2, 2, 3])
    classes = c1.multiselect("Tipo de som", list(CLASSES_SOM), default=["campainha", "batida_porta"],
                             format_func=CLASSES_SOM.get)
    conf_min = c2.slider("Certeza mínima", 0.0, 1.0, 0.0, 0.05,
                         help="Abaixo de 60% o OuviAí não gera aviso: mostra como incerto")
    dmin, dmax = df["momento"].dt.date.min(), df["momento"].dt.date.max()
    periodo = c3.date_input("Período", (dmin, dmax), min_value=dmin, max_value=dmax, format="DD/MM/YYYY")

    f = df[df["classe"].isin(classes) & (df["confianca"] >= conf_min)]
    if isinstance(periodo, tuple) and len(periodo) == 2:
        f = f[(f["momento"].dt.date >= periodo[0]) & (f["momento"].dt.date <= periodo[1])]
    if f.empty:
        estado_vazio("Nenhum som com esses filtros. Tente afrouxar a certeza mínima ou o período.", "🔎")
        return

    fig = px.scatter(f, x="momento", y="som", color="aviso", color_discrete_map=CORES_ROTULO,
                     symbol="aviso", size="confianca", size_max=14,
                     category_orders={"aviso": list(URGENCIAS.values())},
                     hover_data={"mensagem": True, "confianca": ":.0%", "aviso": False, "som": False},
                     labels={"momento": "Quando", "som": "Som", "aviso": "Aviso"},
                     title="Linha do tempo dos sons (passe o mouse e use o zoom)")
    st.plotly_chart(fig, width="stretch")

    f = f.assign(hora=f["momento"].dt.hour)
    fig2 = px.histogram(f, x="hora", color="som", nbins=24, barmode="stack",
                        labels={"hora": "Hora do dia", "count": "Sons", "som": "Som"},
                        title="Em que horário a porta mais chama")
    fig2.update_xaxes(range=[-0.5, 23.5], dtick=2)
    fig2.add_vrect(x0=-0.5, x1=5.5, fillcolor="#1565C0", opacity=0.08, annotation_text="madrugada", line_width=0)
    fig2.add_vrect(x0=21.5, x1=23.5, fillcolor="#1565C0", opacity=0.08, line_width=0)
    st.plotly_chart(fig2, width="stretch")


def _pedidos(pedidos: list[dict]):
    if not pedidos:
        estado_vazio("Nenhum pedido confirmado ainda. Envie um na aba 'Pedir ajuda'.", "📭")
        return
    df = pd.DataFrame(pedidos)
    df["criado_em"] = pd.to_datetime(df["criado_em"])
    df["assunto"] = df["categoria"].map(CATEGORIAS)
    df["urgência"] = df["urgencia"].map(URGENCIAS)

    c1, c2, c3 = st.columns([3, 2, 1], vertical_alignment="bottom")
    cats = c1.multiselect("Assunto", sorted(df["categoria"].unique()), default=sorted(df["categoria"].unique()),
                          format_func=CATEGORIAS.get)
    urgs = c2.multiselect("Urgência", list(URGENCIAS), default=list(URGENCIAS), format_func=URGENCIAS.get)
    so_meus = c3.toggle("Só os meus")

    f = df[df["categoria"].isin(cats) & df["urgencia"].isin(urgs)]
    if so_meus:
        f = f[f["protocolo"].isin({p["protocolo"] for p in st.session_state.meus_pedidos})]
    if f.empty:
        estado_vazio("Nenhum pedido com esses filtros.", "🔎")
        return

    contagem = f.groupby(["assunto", "urgência"]).size().reset_index(name="pedidos")
    st.plotly_chart(px.bar(contagem, x="pedidos", y="assunto", color="urgência", orientation="h",
                           color_discrete_map=CORES_ROTULO, category_orders={"urgência": list(URGENCIAS.values())},
                           labels={"assunto": ""},
                           title="Pedidos por assunto e urgência"), width="stretch")
    st.dataframe(f[["protocolo", "criado_em", "assunto", "urgência", "resumo", "corrigido"]]
                 .rename(columns={"criado_em": "quando", "corrigido": "corrigido pelo cidadão"}),
                 hide_index=True, width="stretch")
