import streamlit as st

from app.acesso import exigir_login
from app.componentes import cabecalho, executar, mensagem
from radar.margem import Parametros, calcular, preco_minimo
from radar.margem.configuracao import obter_configuracao, salvar_configuracao
from radar.valores import decimal_texto, dinheiro_texto, percentual, reais, texto_decimal


def simulacao(p):
    with st.container(border=True):
        st.subheader("Simular uma venda")
        with st.form("simulacao"):
            a, b = st.columns(2)
            preco = a.text_input("Preço de venda (R$)")
            custo = b.text_input("Custo do produto (R$)")
            simular = st.form_submit_button("Calcular margem", type="primary")
        if simular:
            try:
                custo_valor = dinheiro_texto(custo)
                resultado = calcular(dinheiro_texto(preco), custo_valor, p)
                a, b, c = st.columns(3)
                a.metric("Contribuição por venda", reais(resultado.contribuicao))
                b.metric("Margem de contribuição", percentual(resultado.margem_pct))
                try:
                    c.metric("Preço mínimo para o alvo", reais(preco_minimo(custo_valor, p)))
                except ValueError as erro:
                    st.warning(str(erro))
            except ValueError as erro:
                st.error(str(erro))
        st.info("Frete e despesas fixas não entram nesta conta. Contribuição não é lucro líquido.")


def parametros(config):
    p = config.parametros
    with st.container(border=True):
        st.subheader("Parâmetros")
        st.caption("Compartilhados com as estimativas, a pesquisa e o checklist dos fornecedores.")
        with st.form("parametros"):
            a, b, c = st.columns(3)
            comissao = a.text_input("Comissão (%)", texto_decimal(p.comissao_pct * 100))
            tributo = b.text_input("Tributo (%)", texto_decimal(p.tributo_pct * 100))
            alvo = c.text_input("Margem-alvo (%)", texto_decimal(p.margem_alvo_pct * 100))
            tarifa = a.text_input("Tarifa fixa (R$)", texto_decimal(p.tarifa_fixa))
            embalagem = b.text_input("Embalagem (R$)", texto_decimal(p.embalagem))
            outros = c.text_input("Outros por venda (R$)", texto_decimal(p.outros))
            dias = st.number_input("Cotação antiga após quantos dias?", min_value=1, max_value=3650,
                                   value=config.limite_cotacao_dias, step=1)
            salvar = st.form_submit_button("Salvar parâmetros")
        if salvar:
            def salvar_parametros():
                novos = Parametros(decimal_texto(comissao) / 100, decimal_texto(tributo) / 100,
                                   decimal_texto(alvo) / 100, dinheiro_texto(tarifa),
                                   dinheiro_texto(embalagem), dinheiro_texto(outros))
                salvar_configuracao(novos, dias)
            executar(salvar_parametros, "Parâmetros salvos. As estimativas usarão os novos valores.")
        st.caption("Os valores iniciais são ilustrativos. Comissão deve ser confirmada na conta do marketplace; "
                   "tributo não representa enquadramento fiscal. A margem-alvo pode ser simulada livremente, "
                   "mas promoção de fornecedor e decisão de compra exigem pelo menos 20%.")


def mostrar():
    exigir_login()
    cabecalho("Calculadora e parâmetros", "Contribuição e margem por venda, e o preço mínimo para atingir a margem-alvo.")
    mensagem()
    config = obter_configuracao()
    esquerda, direita = st.columns(2)
    with esquerda:
        simulacao(config.parametros)
    with direita:
        parametros(config)
