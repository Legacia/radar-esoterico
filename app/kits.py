from decimal import Decimal
import streamlit as st

from app.acesso import exigir_login
from app.componentes import executar, mensagem
from app.pesquisa import descricao_cotacao
from radar.kits import (ajustar_estoque, consultar_kit, listar_kits, necessidade_conjunta, planejar_kits,
    remover_componente, salvar_componente, salvar_kit)
from radar.mercado import listar_cotacoes
from radar.produtos import listar_produtos
from radar.valores import reais


def mostrar():
    exigir_login()
    st.title("Kits")
    mensagem()
    with st.form("novo_kit"):
        nome = st.text_input("Nome do novo kit")
        criar = st.form_submit_button("Criar kit")
    if criar:
        executar(lambda: salvar_kit(nome), "Kit criado.")
    kits = {k["id"]: k for k in listar_kits()}
    if not kits:
        st.info("Cadastre um kit para compor seus produtos.")
        return
    kit_id = st.selectbox("Kit", list(kits), format_func=lambda i: f"{kits[i]['nome']} · #{i}")
    with st.form(f"planejar_kit_{kit_id}"):
        novo_nome = st.text_input("Nome do kit", kits[kit_id]["nome"])
        quantidade = st.number_input("Kits planejados", min_value=0, value=kits[kit_id]["quantidade_planejada"], step=1)
        salvar = st.form_submit_button("Salvar plano do kit")
    if salvar:
        def atualizar():
            salvar_kit(novo_nome, kit_id)
            planejar_kits(kit_id,quantidade)
        executar(atualizar, "Plano do kit salvo.")
    consulta = consultar_kit(kit_id, max(1,kits[kit_id]["quantidade_planejada"]))
    if consulta["custo_unitario"] is not None:
        st.metric("Custo de um kit", reais(consulta["custo_unitario"]))
        if kits[kit_id]["quantidade_planejada"]:
            st.metric("Custo dos kits planejados", reais(consulta["custo_lote"]))
    else:
        st.info("Complete a composição e a cotação de cada componente para calcular o custo.")
    st.dataframe([{"Produto": i["produto"], "Unidades por kit": i["quantidade"], "Estoque físico": i["estoque_atual"],
        "Custo unitário": reais(Decimal(i["custo_unitario_centavos"]) / 100) if i["custo_unitario_centavos"] is not None else "Sem cotação"}
        for i in consulta["componentes"]], hide_index=True, width="stretch")
    for item in consulta["componentes"]:
        if st.button(f"Remover {item['produto']} do kit", key=f"remover_componente_{kit_id}_{item['produto_id']}"):
            executar(lambda: remover_componente(kit_id,item["produto_id"]), "Componente removido.")
    produtos = {p["id"]: p for p in listar_produtos()}
    if produtos:
        st.subheader("Adicionar ou atualizar componente")
        produto_id = st.selectbox("Componente", list(produtos), format_func=lambda i: f"{produtos[i]['nome']} · #{i}")
        cotacoes = {c["id"]: c for c in listar_cotacoes(produto_id)}
        if cotacoes:
            with st.form(f"componente_{kit_id}_{produto_id}"):
                cotacao_id = st.selectbox("Cotação de custo do componente", list(cotacoes), format_func=lambda i: descricao_cotacao(cotacoes[i]))
                quantidade_item = st.number_input("Unidades desse componente por kit", min_value=1, value=1, step=1)
                adicionar = st.form_submit_button("Salvar componente")
            if adicionar:
                executar(lambda: salvar_componente(kit_id,produto_id,quantidade_item,cotacao_id), "Componente salvo.")
        else:
            st.info("Cadastre uma cotação para este componente em Produtos e SKUs.")
        with st.form(f"estoque_{produto_id}"):
            estoque = st.number_input("Estoque físico atual do componente", min_value=0, value=produtos[produto_id]["estoque_atual"], step=1)
            ajustar = st.form_submit_button("Atualizar estoque físico")
        if ajustar:
            executar(lambda: ajustar_estoque(produto_id,estoque), "Estoque atualizado por produto.")
    st.subheader("Necessidade conjunta dos kits planejados")
    st.dataframe([{"Produto": r["produto"], "Necessário": r["necessario"], "Estoque físico": r["estoque"], "Falta": r["falta"]}
        for r in necessidade_conjunta()], hide_index=True, width="stretch")
    st.caption("O estoque é compartilhado por componente. Este planejamento não baixa nem reserva estoque e não entra automaticamente no orçamento. Planeje a compra de componentes na Decisão de compra.")
