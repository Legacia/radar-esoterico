from datetime import date
import streamlit as st

from app.acesso import exigir_login
from app.componentes import cabecalho, executar, mensagem, selo, tabela_skus
from radar.fornecedores import listar_fornecedores
from radar.margem.configuracao import obter_configuracao
from radar.produtos import listar_produtos, listar_skus, registrar_cotacao, salvar_produto
from radar.valores import dinheiro_texto

CONFERENCIAS = (("especificacoes_conferidas", "Especificações"), ("procedencia_conferida", "Procedência"),
                ("qualidade_conferida", "Qualidade"))


def formulario_produto(produto=None):
    p = produto or {}
    with st.form(f"produto_{p.get('id', 'novo')}"):
        a, b, c = st.columns(3)
        nome = a.text_input("Nome do produto", p.get("nome", ""))
        familia = b.text_input("Família", p.get("familia") or "")
        status = c.text_input("Status do produto", p.get("status", "Candidato"))
        st.markdown("**Avaliação do produto**")
        a, b, c = st.columns(3)
        especificacoes = a.checkbox("Especificações conferidas", bool(p.get("especificacoes_conferidas")))
        procedencia = b.checkbox("Procedência conferida", bool(p.get("procedencia_conferida")))
        qualidade = c.checkbox("Qualidade conferida pela Anna", bool(p.get("qualidade_conferida")))
        salvar = st.form_submit_button("Salvar produto", type="primary")
    if salvar:
        executar(lambda: salvar_produto(nome, familia, status, especificacoes, procedencia,
                                        qualidade, produto_id=p.get("id")), "Produto salvo.")


def formulario_cotacao(produto_id):
    fornecedores = listar_fornecedores()
    if not fornecedores:
        st.info("Cadastre um fornecedor na tela Fornecedores para lançar uma cotação.")
        return
    fornecedores_id = {f["id"]: f for f in fornecedores}
    st.caption("Repita o código e informe a nova data para recotar um SKU. O preço de venda é sua estimativa conservadora, ainda sem pesquisa de mercado automática.")
    with st.form(f"cotacao_{produto_id}"):
        a, b, c = st.columns(3)
        fornecedor = a.selectbox("Fornecedor da cotação", list(fornecedores_id),
                                 format_func=lambda i: fornecedores_id[i]["nome"])
        codigo = b.text_input("Código no fornecedor")
        data = c.date_input("Data da cotação", value=date.today(), max_value=date.today(), format="DD/MM/YYYY")
        custo = a.text_input("Custo unitário (R$)")
        quantidade = b.number_input("Quantidade mínima", min_value=1, value=1, step=1)
        preco = c.text_input("Preço conservador de venda (R$), opcional")
        salvar = st.form_submit_button("Salvar cotação", type="primary")
    if salvar:
        executar(lambda: registrar_cotacao(fornecedor, produto_id, codigo, dinheiro_texto(custo),
                  quantidade, data, dinheiro_texto(preco) if preco.strip() else None), "Cotação registrada.")


def mostrar():
    exigir_login()
    cabecalho("Produtos e SKUs", "Catálogo dos candidatos e as cotações de cada fornecedor, sempre com a data.")
    mensagem()
    with st.expander("Cadastrar produto", icon=":material/add:"):
        formulario_produto()
    produtos = listar_produtos()
    if not produtos:
        st.info("Cadastre um produto para começar a registrar as cotações.")
        return
    st.dataframe([{"Produto": p["nome"], "Família": p["familia"] or "Não informada", "Status": p["status"],
        "Conferências": f"{sum(bool(p[c]) for c, _ in CONFERENCIAS)} de 3",
        "Validado para compra": "Sim" if p["validado"] else "Não", "Estoque físico": p["estoque_atual"]}
        for p in produtos], hide_index=True, width="stretch")
    por_id = {p["id"]: p for p in produtos}
    escolhido = st.selectbox("Produto", list(por_id), format_func=lambda i: por_id[i]["nome"])
    produto = por_id[escolhido]
    with st.container(border=True):
        st.subheader(produto["nome"])
        st.markdown(" ".join([selo(produto["status"], "blue"), selo(produto["familia"] or "Família não informada", "gray")]
            + [selo(rotulo, "green" if produto[campo] else "orange") for campo, rotulo in CONFERENCIAS]))
    cotacoes, registrar, editar = st.tabs(["Cotações deste produto", "Registrar cotação de SKU", "Editar produto e avaliação"])
    with cotacoes:
        tabela_skus(listar_skus(produto_id=escolhido), obter_configuracao())
    with registrar:
        formulario_cotacao(escolhido)
    with editar:
        formulario_produto(produto)
