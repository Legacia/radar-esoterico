from decimal import Decimal
import streamlit as st

from app.acesso import exigir_login
from app.componentes import cabecalho, executar, mensagem, selo
from app.navegacao import link
from app.pesquisa import descricao_cotacao
from radar.kits import (ajustar_estoque, consultar_kit, listar_kits, necessidade_conjunta, planejar_kits,
    remover_componente, salvar_componente, salvar_kit)
from radar.mercado import listar_cotacoes
from radar.produtos import listar_produtos
from radar.valores import reais


def plano_do_kit(kit_id, kit):
    with st.form(f"planejar_kit_{kit_id}"):
        a, b = st.columns(2)
        novo_nome = a.text_input("Nome do kit", kit["nome"])
        quantidade = b.number_input("Kits planejados", min_value=0, value=kit["quantidade_planejada"], step=1,
                                    help="Zero retira o kit da necessidade conjunta.")
        salvar = st.form_submit_button("Salvar plano do kit", type="primary")
    if salvar:
        def atualizar():
            salvar_kit(novo_nome, kit_id)
            planejar_kits(kit_id,quantidade)
        executar(atualizar, "Plano do kit salvo.")


def composicao(kit_id, kit):
    consulta = consultar_kit(kit_id, max(1,kit["quantidade_planejada"]))
    a, b = st.columns(2)
    if consulta["custo_unitario"] is not None:
        a.metric("Custo de um kit", reais(consulta["custo_unitario"]))
        if kit["quantidade_planejada"]:
            b.metric("Custo dos kits planejados", reais(consulta["custo_lote"]))
    else:
        st.info("Complete a composição e a cotação de cada componente para calcular o custo.")
    for item in consulta["componentes"]:
        with st.container(border=True):
            x, y = st.columns([4, 1])
            custo = (reais(Decimal(item["custo_unitario_centavos"]) / 100) if item["custo_unitario_centavos"] is not None
                     else None)
            x.markdown(f"**{item['produto']}** · {item['quantidade']} por kit · estoque físico {item['estoque_atual']}  \n"
                       + (f":gray[Custo unitário {custo}]" if custo else selo("Sem cotação", "orange")))
            if y.button("Remover", key=f"remover_componente_{kit_id}_{item['produto_id']}",
                        icon=":material/delete:", help=f"Remover {item['produto']} do kit"):
                executar(lambda: remover_componente(kit_id,item["produto_id"]), "Componente removido.")
    if not consulta["componentes"]:
        st.caption("Kit ainda sem componentes.")
    st.dataframe([{"Produto": i["produto"], "Unidades por kit": i["quantidade"], "Estoque físico": i["estoque_atual"],
        "Custo unitário": reais(Decimal(i["custo_unitario_centavos"]) / 100) if i["custo_unitario_centavos"] is not None else "Sem cotação"}
        for i in consulta["componentes"]], hide_index=True, width="stretch")


def componentes(kit_id):
    produtos = {p["id"]: p for p in listar_produtos()}
    if not produtos:
        st.info("Cadastre produtos em Produtos e SKUs para compor o kit.")
        return
    produto_id = st.selectbox("Componente", list(produtos), format_func=lambda i: produtos[i]["nome"])
    cotacoes = {c["id"]: c for c in listar_cotacoes(produto_id)}
    if cotacoes:
        with st.form(f"componente_{kit_id}_{produto_id}"):
            a, b = st.columns([3, 1])
            cotacao_id = a.selectbox("Cotação de custo do componente", list(cotacoes), format_func=lambda i: descricao_cotacao(cotacoes[i]))
            quantidade_item = b.number_input("Unidades desse componente por kit", min_value=1, value=1, step=1)
            adicionar = st.form_submit_button("Salvar componente", type="primary")
        if adicionar:
            executar(lambda: salvar_componente(kit_id,produto_id,quantidade_item,cotacao_id), "Componente salvo.")
    else:
        st.info("Cadastre uma cotação para este componente em Produtos e SKUs.")
        link("produtos", "Abrir Produtos e SKUs", ":material/arrow_forward:")
    with st.form(f"estoque_{produto_id}"):
        estoque = st.number_input("Estoque físico atual do componente", min_value=0, value=produtos[produto_id]["estoque_atual"], step=1)
        ajustar = st.form_submit_button("Atualizar estoque físico")
    if ajustar:
        executar(lambda: ajustar_estoque(produto_id,estoque), "Estoque atualizado por produto.")


def mostrar():
    exigir_login()
    cabecalho("Kits", "Composição por produto, com o estoque controlado por componente.")
    mensagem()
    with st.expander("Criar kit", icon=":material/add:", expanded=not listar_kits()):
        with st.form("novo_kit"):
            nome = st.text_input("Nome do novo kit")
            criar = st.form_submit_button("Criar kit", type="primary")
        if criar:
            executar(lambda: salvar_kit(nome), "Kit criado.")
    kits = {k["id"]: k for k in listar_kits()}
    if not kits:
        st.info("Cadastre um kit para compor seus produtos.")
        return
    kit_id = st.selectbox("Kit", list(kits), format_func=lambda i: f"{kits[i]['nome']} · {kits[i]['quantidade_planejada']} planejados")
    esquerda, direita = st.columns([1.2, 1])
    with esquerda:
        with st.container(border=True):
            st.subheader("Composição e custo")
            composicao(kit_id, kits[kit_id])
    with direita:
        with st.container(border=True):
            st.subheader("Plano do kit")
            plano_do_kit(kit_id, kits[kit_id])
        with st.container(border=True):
            st.subheader("Adicionar ou atualizar componente")
            componentes(kit_id)
    with st.container(border=True):
        st.subheader("Necessidade conjunta dos kits planejados")
        st.dataframe([{"Produto": r["produto"], "Necessário": r["necessario"], "Estoque físico": r["estoque"], "Falta": r["falta"]}
            for r in necessidade_conjunta()], hide_index=True, width="stretch")
        st.caption("O estoque é compartilhado por componente. Este planejamento não baixa nem reserva estoque e não entra automaticamente no orçamento. Planeje a compra de componentes na Decisão de compra.")
        link("compras", "Abrir Decisão de compra", ":material/arrow_forward:")
