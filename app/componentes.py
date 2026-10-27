"""Componentes de apresentação; validação e cálculos ficam em radar/."""
from decimal import Decimal
import streamlit as st

from radar.margem import preco_minimo
from radar.produtos import cotacao_antiga, estimar_margem
from radar.valores import data_br, percentual, reais


ESTILO = """
<style>
.block-container {max-width: 1480px; padding-top: 2.2rem; padding-bottom: 4rem;}
h1 {letter-spacing: -0.01em;}
[data-testid="stMain"] [data-testid="stCaptionContainer"] {color: #4a5566;}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"], [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {color: #b8c2d0; opacity: 1;}
/* Cartões de indicador: fundo claro e faixa à esquerda, como na referência. */
[data-testid="stMetric"] {background: #ffffff; border: 1px solid #d8dde5; border-left: 3px solid #24406f;
    border-radius: 8px; padding: 12px 16px;}
[data-testid="stMetricValue"] {font-size: 1.35rem; font-weight: 600; font-variant-numeric: tabular-nums;}
[data-testid="stMetricLabel"] p {font-size: 0.82rem; color: #4a5566;}
[data-testid="stExpander"] details {background: #ffffff; border-radius: 8px;}
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {background: #ffffff;}
/* Barra lateral escura com marca no topo. */
[data-testid="stSidebarNav"]::before {content: "Radar Esotérico\\A Tenda da Bruxa 2.0"; white-space: pre;
    display: block; color: #ffffff; font-weight: 600; font-size: 1rem; line-height: 1.5;
    padding: 0.3rem 1rem 0.8rem; border-bottom: 1px solid #2b3a50; margin-bottom: 0.5rem;}
[data-testid="stSidebarNavLink"][aria-current="page"] {box-shadow: inset 3px 0 0 #8fb3ff;}
[data-testid="stSidebarNavSeparator"] {border-color: #2b3a50;}
[data-testid="stSidebarUserContent"] {color: #c9d2de; font-size: 0.85rem;}
</style>
"""


def aplicar_estilo():
    st.markdown(ESTILO, unsafe_allow_html=True)


def cabecalho(titulo, descricao=None):
    st.title(titulo)
    if descricao:
        st.caption(descricao)


def _limpo(texto):
    return str(texto).replace("[", "(").replace("]", ")")


def selo(texto, cor="gray"):
    """Selo colorido em markdown: green, orange, red, yellow, blue, violet ou gray."""
    return f":{cor}-badge[{_limpo(texto)}]"


def selos_criterios(criterios):
    """Uma linha de selos: verde para cumprido, laranja para pendente."""
    st.markdown(" ".join(selo(("✓ " if ok else "○ ") + nome, "green" if ok else "orange")
                         for nome, ok in criterios.items()))


def mensagem():
    if texto := st.session_state.pop("mensagem", None):
        st.success(texto)


def executar(acao, sucesso):
    try:
        acao()
    except ValueError as erro:
        st.error(str(erro))
    else:
        st.session_state["mensagem"] = sucesso
        st.rerun()


def tabela_skus(skus, configuracao):
    if not skus:
        st.info("Nenhuma cotação cadastrada.")
        return
    linhas = []
    for sku in skus:
        margem = estimar_margem(sku, configuracao.parametros)
        try:
            minimo = reais(preco_minimo(Decimal(sku["custo_unitario_centavos"]) / 100, configuracao.parametros))
        except ValueError:
            minimo = "Alvo inviável"
        linhas.append({
            "Código": sku["codigo"], "Produto": sku["produto"], "Fornecedor": sku["fornecedor"],
            "Custo": reais(Decimal(sku["custo_unitario_centavos"]) / 100),
            "Quantidade mínima": sku["quantidade_minima"], "Cotação": data_br(sku["data_cotacao"]),
            "Cotação antiga": "Sim" if cotacao_antiga(sku["data_cotacao"], configuracao.limite_cotacao_dias) else "Não",
            "Preço conservador": reais(Decimal(sku["preco_venda_centavos"]) / 100) if sku["preco_venda_centavos"] else "Não informado",
            "Contribuição": reais(margem.contribuicao) if margem else "Sem estimativa",
            "Margem estimada": percentual(margem.margem_pct) if margem else "Sem estimativa",
            "Preço mínimo para o alvo": minimo,
        })
    st.dataframe(linhas, hide_index=True, width="stretch")
    if any(cotacao_antiga(s["data_cotacao"], configuracao.limite_cotacao_dias) for s in skus):
        st.warning(f"Há cotações com mais de {configuracao.limite_cotacao_dias} dias. Confirme os valores com o fornecedor.")
    st.caption("Exibida a cotação mais recente de cada código por fornecedor. As anteriores são preservadas.")
