from datetime import date
import streamlit as st

from app.acesso import exigir_login
from app.componentes import executar, mensagem, tabela_skus
from radar.fornecedores import listar_fornecedores
from radar.margem.configuracao import obter_configuracao
from radar.produtos import listar_produtos, listar_skus, registrar_cotacao, salvar_produto
from radar.valores import dinheiro_texto


def formulario_produto(produto=None):
    p = produto or {}
    with st.form(f"produto_{p.get('id', 'novo')}"):
        nome = st.text_input("Nome do produto", p.get("nome", ""))
        familia = st.text_input("Família", p.get("familia") or "")
        status = st.text_input("Status do produto", p.get("status", "Candidato"))
        especificacoes = st.checkbox("Especificações conferidas", bool(p.get("especificacoes_conferidas")))
        procedencia = st.checkbox("Procedência conferida", bool(p.get("procedencia_conferida")))
        qualidade = st.checkbox("Qualidade conferida pela Anna", bool(p.get("qualidade_conferida")))
        salvar = st.form_submit_button("Salvar produto")
    if salvar:
        executar(lambda: salvar_produto(nome, familia, status, especificacoes, procedencia,
                                        qualidade, produto_id=p.get("id")), "Produto salvo.")


def mostrar():
    exigir_login()
    st.title("Produtos e SKUs")
    mensagem()
    with st.expander("Cadastrar produto"):
        formulario_produto()
    produtos = listar_produtos()
    if not produtos:
        st.info("Cadastre um produto para começar a registrar as cotações.")
        return
    por_id = {p["id"]: p for p in produtos}
    escolhido = st.selectbox("Produto", list(por_id), format_func=lambda i: f"{por_id[i]['nome']} · #{i}")
    produto = por_id[escolhido]
    st.write(f"Família: {produto['familia'] or 'Não informada'} · Status: {produto['status']}")
    with st.expander("Editar produto e avaliação"):
        formulario_produto(produto)
    st.subheader("Cotações deste produto")
    tabela_skus(listar_skus(produto_id=escolhido), obter_configuracao())
    fornecedores = listar_fornecedores()
    if not fornecedores:
        st.info("Cadastre um fornecedor na tela Fornecedores para lançar uma cotação.")
        return
    fornecedores_id = {f["id"]: f for f in fornecedores}
    st.subheader("Registrar cotação de SKU")
    st.caption("Repita o código e informe a nova data para recotar um SKU. O preço de venda é sua estimativa conservadora, ainda sem pesquisa de mercado automática.")
    with st.form(f"cotacao_{escolhido}"):
        fornecedor = st.selectbox("Fornecedor da cotação", list(fornecedores_id),
                                 format_func=lambda i: f"{fornecedores_id[i]['nome']} · #{i}")
        codigo = st.text_input("Código no fornecedor")
        custo = st.text_input("Custo unitário (R$)")
        quantidade = st.number_input("Quantidade mínima", min_value=1, value=1, step=1)
        data = st.date_input("Data da cotação", value=date.today(), max_value=date.today())
        preco = st.text_input("Preço conservador de venda (R$), opcional")
        salvar = st.form_submit_button("Salvar cotação")
    if salvar:
        executar(lambda: registrar_cotacao(fornecedor, escolhido, codigo, dinheiro_texto(custo),
                  quantidade, data, dinheiro_texto(preco) if preco.strip() else None), "Cotação registrada.")
