from decimal import Decimal
import streamlit as st

from app.acesso import exigir_login
from app.componentes import executar, mensagem
from app.pesquisa import descricao_cotacao
from radar.compras import avaliar_lote, remover_plano, salvar_orcamento, salvar_plano
from radar.mercado import listar_cotacoes
from radar.produtos import listar_produtos
from radar.valores import data_br, dinheiro_texto, percentual, reais, texto_decimal


def mostrar():
    exigir_login()
    st.title("Decisão de compra")
    mensagem()
    st.info("Esta tela só planeja o lote e verifica critérios. Não faz compras nem movimenta dinheiro.")
    lote = avaliar_lote()
    orcamento = lote["orcamento"]
    with st.expander("Configurar orçamento e reserva"):
        with st.form("orcamento"):
            total = st.text_input("Orçamento do lote (R$)", texto_decimal(Decimal(orcamento["total_centavos"]) / 100))
            reserva = st.text_input("Reserva de reposição (R$)", texto_decimal(Decimal(orcamento["reserva_centavos"]) / 100))
            salvar = st.form_submit_button("Salvar orçamento")
        if salvar:
            executar(lambda: salvar_orcamento(dinheiro_texto(total),dinheiro_texto(reserva)), "Orçamento salvo.")
    a,b,c = st.columns(3)
    a.metric("Orçamento", reais(Decimal(orcamento["total_centavos"]) / 100))
    b.metric("Comprometido", reais(Decimal(lote["comprometido_centavos"]) / 100))
    c.metric("Disponível após reserva", reais(Decimal(lote["disponivel_centavos"]) / 100))
    if lote["excede_disponivel"]:
        st.warning("O total planejado ultrapassa o orçamento após a reserva de reposição.")
    for item in lote["itens"]:
        with st.expander(f"{item['produto']} · {'Pronto' if item['pronto'] else 'Pendente'}", expanded=True):
            st.write(f"{item['quantidade']} unidades · {reais(Decimal(item['valor_centavos']) / 100)} · {percentual(item['percentual_orcamento'])} do orçamento")
            st.write(f"{item['fornecedor']} · {item['codigo']} · cotação de {data_br(item['data_cotacao'])}")
            st.write(f"Contribuição por venda: {reais(item['contribuicao'])} · Margem: {percentual(item['margem'])}")
            for criterio, ok in item["criterios"].items():
                st.write(f"{'✅' if ok else '⬜'} {criterio}")
            if item["acima_vinte"]:
                st.warning("Produto ainda não validado compromete mais de 20% do orçamento.")
            if st.button("Retirar do plano", key=f"retirar_{item['produto_id']}"):
                executar(lambda: remover_plano(item["produto_id"]), "Produto retirado do plano.")
    produtos = {p["id"]: p for p in listar_produtos()}
    if not produtos:
        st.info("Cadastre produtos e cotações antes de planejar o lote.")
        return
    st.subheader("Adicionar ou editar produto no plano")
    produto_id = st.selectbox("Produto do plano", list(produtos), format_func=lambda i: f"{produtos[i]['nome']} · #{i}")
    cotacoes = {c["id"]: c for c in listar_cotacoes(produto_id)}
    if not cotacoes:
        st.info("Este produto precisa de uma cotação de fornecedor.")
        return
    atual = next((i for i in lote["itens"] if i["produto_id"] == produto_id), {})
    ids = list(cotacoes)
    cotacao_id = st.selectbox("Cotação para o plano", ids,
        index=ids.index(atual["sku_fornecedor_id"]) if atual.get("sku_fornecedor_id") in ids else 0,
        format_func=lambda i: descricao_cotacao(cotacoes[i]))
    produto = produtos[produto_id]
    with st.form(f"plano_{produto_id}_{cotacao_id}"):
        quantidade = st.number_input("Quantidade planejada", min_value=1, value=atual.get("quantidade", cotacoes[cotacao_id]["quantidade_minima"]), step=1)
        preco_inicial = atual.get("preco_venda_centavos") or cotacoes[cotacao_id]["preco_venda_centavos"]
        preco = st.text_input("Preço conservador de venda no plano (R$)", texto_decimal(Decimal(preco_inicial) / 100) if preco_inicial else "")
        demanda = st.checkbox("Demanda confirmada", bool(atual.get("demanda_confirmada")))
        demanda_texto = st.text_area("Justificativa de demanda", atual.get("justificativa_demanda", ""))
        concorrencia = st.checkbox("Concorrência confirmada", bool(atual.get("concorrencia_confirmada")))
        concorrencia_texto = st.text_area("Justificativa de concorrência", atual.get("justificativa_concorrencia", ""))
        validado = st.checkbox("Produto validado", bool(produto["validado"]))
        validacao_texto = st.text_area("Justificativa da validação", produto["justificativa_validacao"])
        salvar = st.form_submit_button("Salvar planejamento")
    if salvar:
        executar(lambda: salvar_plano(produto_id,cotacao_id,quantidade,dinheiro_texto(preco),
            demanda,demanda_texto,concorrencia,concorrencia_texto,validado,validacao_texto), "Planejamento salvo e critérios recalculados.")
