"""Componentes visuais reutilizáveis.

Público principal: pessoa com deficiência auditiva. Tudo que é aviso tem
cor + ícone + texto (nunca só a cor) e não depende de som.
"""
import html

import streamlit as st

# fundo, texto, ícone, rótulo — contraste ≥ 4,5:1 (WCAG 1.4.3)
NIVEIS = {
    "alta":  ("#B71C1C", "#FFFFFF", "🔴", "URGENTE"),
    "media": ("#F9A825", "#000000", "🟠", "ATENÇÃO"),
    "baixa": ("#2E7D32", "#FFFFFF", "🟢", "TRANQUILO"),
}
NIVEIS_ALTO_CONTRASTE = {
    "alta":  ("#000000", "#FFFF00", "🔴", "URGENTE"),
    "media": ("#000000", "#FFFFFF", "🟠", "ATENÇÃO"),
    "baixa": ("#FFFFFF", "#000000", "🟢", "TRANQUILO"),
}

CATEGORIAS = {
    "saude_auditiva": "👂 Saúde auditiva",
    "beneficio_bpc": "💰 Benefício (BPC / CadÚnico)",
    "direitos_idoso": "🧓 Direitos da pessoa idosa",
    "transporte": "🚌 Transporte",
    "manutencao_urbana": "🚧 Calçada e rua",
    "golpe": "⚠️ Suspeita de golpe",
    "outro": "📄 Outro assunto",
}
URGENCIAS = {"alta": "🔴 Urgente", "media": "🟠 Atenção", "baixa": "🟢 Tranquilo"}
CLASSES_SOM = {"campainha": "🔔 Campainha", "batida_porta": "🚪 Batida na porta", "ambiente": "🔈 Ambiente"}
CORES_GRAFICO = {"alta": "#B71C1C", "media": "#F9A825", "baixa": "#2E7D32"}
# mesmas cores, chaveadas pelo rótulo que aparece na legenda dos gráficos
CORES_ROTULO = {URGENCIAS[k]: v for k, v in CORES_GRAFICO.items()}


def cartao(nivel: str, titulo: str, texto: str = "", rodape: str = "", grande: bool = False):
    """Usado no resultado da triagem, no último aviso da casa, na lista de avisos e em 'meus pedidos'."""
    tabela = NIVEIS_ALTO_CONTRASTE if st.session_state.get("alto_contraste") else NIVEIS
    fundo, fonte, icone, rotulo = tabela[nivel]
    tamanho = "1.6rem" if grande else "1.05rem"
    cor = f"color:{fonte} !important"
    partes = [f"<div style='{cor};font-size:{tamanho};font-weight:700'>{icone} {rotulo} · {html.escape(titulo)}</div>"]
    if texto:
        partes.append(f"<div style='{cor};margin-top:6px'>{html.escape(texto)}</div>")
    if rodape:
        partes.append(f"<div style='{cor};margin-top:6px;font-size:.85rem'>{html.escape(rodape)}</div>")
    st.markdown(
        f"<div role='{'alert' if nivel == 'alta' else 'status'}' aria-live='polite' "
        f"style='background:{fundo};color:{fonte};padding:14px 16px;border-radius:10px;"
        f"margin-bottom:10px;border:2px solid {fonte}'>{''.join(partes)}</div>",
        unsafe_allow_html=True,
    )


def estado_vazio(mensagem: str, icone: str = "🗂️"):
    st.markdown(
        f"<div style='text-align:center;padding:28px;border:2px dashed #888;border-radius:10px'>"
        f"<div style='font-size:2rem'>{icone}</div><div>{html.escape(mensagem)}</div></div>",
        unsafe_allow_html=True,
    )


def porcentagem(valor: float | None) -> str:
    return "—" if valor is None else f"{valor:.0%}"


def aplicar_tema():
    """Fonte maior para todos; alto contraste opcional (preto/amarelo)."""
    css = "html, body, [class*='st-'] { font-size: 1.05rem; } button:focus-visible { outline: 3px solid #1565C0 !important; }"
    if st.session_state.get("alto_contraste"):
        # alvos pontuais: um seletor genérico (*) pintaria de branco o texto dos cartões claros
        css += (
            ".stApp, [data-testid='stHeader'], [data-testid='stSidebar'] { background:#000 !important; }"
            ".stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4,"
            " [data-testid='stCaptionContainer'], [data-testid='stMetricLabel'], [data-testid='stMetricValue'],"
            " [data-testid='stTab'], [data-testid='stWidgetLabel'] { color:#FFF !important; }"
            ".stApp button { background:#000 !important; color:#FFFF00 !important; border:2px solid #FFFF00 !important; }"
            ".stApp button p { color:#FFFF00 !important; }"
            "[data-testid='stAlertContainer'] { background:#000 !important; border:2px solid #FFFF00 !important; }"
            ".stApp input, .stApp textarea { background:#111 !important; color:#FFF !important;"
            " border:2px solid #FFFF00 !important; }"
        )
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
