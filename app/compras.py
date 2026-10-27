from decimal import Decimal
import streamlit as st

from app.acesso import exigir_login
from app.componentes import cabecalho, executar, mensagem, selo, selos_criterios
from app.pesquisa import descricao_cotacao
from radar.compras import avaliar_lote, remover_plano, salvar_orcamento, salvar_plano
from radar.mercado import listar_cotacoes
from radar.produtos import listar_produtos
from radar.valores import data_br, dinheiro_texto, percentual, reais, texto_decimal


def _reais(centavos):
    return reais(Decimal(centavos) / 100)


def resumo_orcamento(lote):
    orcamento = lote["orcamento"]
    a, b, c, d = st.columns(4)
    a.metric("Orçamento", _reais(orcamento["total_centavos"]))
    b.metric("Reserva de reposição", _reais(orcamento["reserva_centavos"]))
    c.metric("Comprometido", _reais(lote["comprometido_centavos"]), help="Soma de todos os itens do plano, prontos ou pendentes.")
    d.metric("Disponível após reserva", _reais(lote["disponivel_centavos"]))
    livre = orcamento["total_centavos"] - orcamento["reserva_centavos"]
    uso = min(100, lote["comprometido_centavos"] * 100 // livre) if livre > 0 else 100
    st.progress(uso, text=f"{uso}% do valor disponível para compra (orçamento menos reserva)")
    if lote["excede_disponivel"]:
        st.warning("O total planejado ultrapassa o orçamento após a reserva de reposição.")
    with st.expander("Configurar orçamento e reserva", icon=":material/tune:"):
        with st.form("orcamento"):
            a, b = st.columns(2)
            total = a.text_input("Orçamento do lote (R$)", texto_decimal(Decimal(orcamento["total_centavos"]) / 100))
            reserva = b.text_input("Reserva de reposição (R$)", texto_decimal(Decimal(orcamento["reserva_centavos"]) / 100))
            salvar = st.form_submit_button("Salvar orçamento", type="primary")
        if salvar:
            executar(lambda: salvar_orcamento(dinheiro_texto(total),dinheiro_texto(reserva)), "Orçamento salvo.")


def cartao_item(item):
    with st.container(border=True):
        a, b = st.columns([4, 1])
        a.markdown(f"**{item['produto']}** {selo('Pronto', 'green') if item['pronto'] else selo('Pendente', 'orange')}"
                   + ("" if item["validado"] else f" {selo('Não validado', 'yellow')}"))
        if b.button("Retirar do plano", key=f"retirar_{item['produto_id']}", icon=":material/remove_shopping_cart:"):
            executar(lambda: remover_plano(item["produto_id"]), "Produto retirado do plano.")
        x, y, z, w = st.columns(4)
        x.markdown(f"**Quantidade**  \n{item['quantidade']} unidades")
        y.markdown(f"**Valor**  \n{_reais(item['valor_centavos'])} · {percentual(item['percentual_orcamento'])} do orçamento")
        z.markdown(f"**Contribuição por venda**  \n{reais(item['contribuicao'])}")
        w.markdown(f"**Margem**  \n{percentual(item['margem'])}")
        st.caption(f"{item['fornecedor']} · {item['codigo']} · cotação de {data_br(item['data_cotacao'])}")
        selos_criterios(item["criterios"])
        if item["acima_vinte"]:
            st.warning("Produto ainda não validado compromete mais de 20% do orçamento.")


def formulario_plano(lote):
    produtos = {p["id"]: p for p in listar_produtos()}
    if not produtos:
        st.info("Cadastre produtos e cotações antes de planejar o lote.")
        return
    produto_id = st.selectbox("Produto do plano", list(produtos), format_func=lambda i: produtos[i]["nome"])
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
        a, b = st.columns(2)
        quantidade = a.number_input("Quantidade planejada", min_value=1, value=atual.get("quantidade", cotacoes[cotacao_id]["quantidade_minima"]), step=1)
        preco_inicial = atual.get("preco_venda_centavos") or cotacoes[cotacao_id]["preco_venda_centavos"]
        preco = b.text_input("Preço conservador de venda no plano (R$)", texto_decimal(Decimal(preco_inicial) / 100) if preco_inicial else "")
        st.markdown("**Confirmações manuais**")
        st.caption("Cada confirmação exige uma justificativa com a evidência que vocês encontraram.")
        a, b, c = st.columns(3)
        demanda = a.checkbox("Demanda confirmada", bool(atual.get("demanda_confirmada")))
        demanda_texto = a.text_area("Justificativa de demanda", atual.get("justificativa_demanda", ""))
        concorrencia = b.checkbox("Concorrência confirmada", bool(atual.get("concorrencia_confirmada")))
        concorrencia_texto = b.text_area("Justificativa de concorrência", atual.get("justificativa_concorrencia", ""))
        validado = c.checkbox("Produto validado", bool(produto["validado"]))
        validacao_texto = c.text_area("Justificativa da validação", produto["justificativa_validacao"])
        salvar = st.form_submit_button("Salvar planejamento", type="primary")
    if salvar:
        executar(lambda: salvar_plano(produto_id,cotacao_id,quantidade,dinheiro_texto(preco),
            demanda,demanda_texto,concorrencia,concorrencia_texto,validado,validacao_texto), "Planejamento salvo e critérios recalculados.")


def mostrar():
    exigir_login()
    cabecalho("Decisão de compra", "Orçamento, reserva e os seis critérios de cada produto do primeiro lote.")
    mensagem()
    st.info("Esta tela só planeja o lote e verifica critérios. Não faz compras nem movimenta dinheiro.")
    lote = avaliar_lote()
    resumo_orcamento(lote)
    st.subheader(f"Produtos no plano · {sum(i['pronto'] for i in lote['itens'])} de {len(lote['itens'])} prontos")
    if not lote["itens"]:
        st.caption("Nenhum produto no plano ainda. Adicione abaixo.")
    for item in lote["itens"]:
        cartao_item(item)
    st.caption("Pronto exige os seis critérios: Fornecedor, Produto, Margem, Demanda, Concorrência e Estoque. "
               "Produto não validado não pode passar de 20% do orçamento.")
    with st.container(border=True):
        st.subheader("Adicionar ou editar produto no plano")
        formulario_plano(lote)
