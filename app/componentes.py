"""Componentes de apresentação; validação e cálculos ficam em radar/."""
from decimal import Decimal
import streamlit as st

from radar.margem import preco_minimo
from radar.produtos import cotacao_antiga, estimar_margem
from radar.valores import data_br, percentual, reais


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
