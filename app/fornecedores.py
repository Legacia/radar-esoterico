from datetime import date
from decimal import Decimal
import streamlit as st

from app.acesso import exigir_login
from app.componentes import executar, mensagem, tabela_skus
from radar.fornecedores import (ETAPAS, alterar_etapa, avaliar_promocao, listar_fornecedores,
    listar_interacoes, obter_fornecedor, promover, registrar_interacao, salvar_fornecedor)
from radar.margem.configuracao import obter_configuracao
from radar.produtos import listar_skus
from radar.valores import data_br, dinheiro_texto, percentual, reais, texto_decimal


def formulario_fornecedor(fornecedor=None):
    f = fornecedor or {}
    with st.form(f"fornecedor_{f.get('id', 'novo')}"):
        nome = st.text_input("Nome do fornecedor", f.get("nome", ""))
        cnpj = st.text_input("CNPJ", f.get("cnpj") or "")
        contato = st.text_input("Contato", f.get("contato") or "")
        minimo = st.text_input("Pedido mínimo (R$)", texto_decimal(Decimal(f.get("pedido_minimo_centavos", 0)) / 100))
        prazo = st.text_input("Prazo", f.get("prazo") or "")
        pagamento = st.text_input("Condição de pagamento", f.get("condicao_pagamento") or "")
        st.caption("Confirmações manuais, feitas por vocês após verificar as informações.")
        cnpj_ok = st.checkbox("CNPJ verificado", bool(f.get("cnpj_verificado")))
        condicoes_ok = st.checkbox("Condições comerciais verificadas", bool(f.get("condicoes_verificadas")))
        nota = st.checkbox("Emite nota fiscal", bool(f.get("emite_nota")))
        amostra = st.checkbox("Amostra avaliada pela Anna (especificações, procedência e qualidade)", bool(f.get("amostra_avaliada")))
        reposicao = st.checkbox("Reposição confirmada", bool(f.get("reposicao_confirmada")))
        salvar = st.form_submit_button("Salvar fornecedor")
    if salvar:
        executar(lambda: salvar_fornecedor(nome, cnpj, contato, dinheiro_texto(minimo), prazo,
                pagamento, cnpj_ok, condicoes_ok, nota, amostra, reposicao,
                fornecedor_id=f.get("id")), "Fornecedor salvo.")


def mostrar():
    exigir_login()
    st.title("Fornecedores")
    mensagem()
    with st.expander("Cadastrar fornecedor"):
        formulario_fornecedor()
    fornecedores = listar_fornecedores()
    st.subheader("Por etapa")
    for etapa in ETAPAS:
        grupo = [f for f in fornecedores if f["status"] == etapa]
        with st.expander(f"{etapa} ({len(grupo)})"):
            for f in grupo:
                st.write(f"{f['nome']} · #{f['id']}")
    if not fornecedores:
        st.info("Nenhum fornecedor cadastrado.")
        return
    por_id = {f["id"]: f for f in fornecedores}
    escolhido = st.selectbox("Abrir ficha", list(por_id), format_func=lambda i: f"{por_id[i]['nome']} · #{i}")
    f = obter_fornecedor(escolhido)
    st.subheader(f"{f['nome']} · {f['status']}")
    st.write(f"Pedido mínimo: {reais(Decimal(f['pedido_minimo_centavos']) / 100)}")
    st.write(f"Prazo: {f['prazo'] or 'Não informado'} · Pagamento: {f['condicao_pagamento'] or 'Não informado'}")
    st.write(f"Última cotação: {data_br(f['data_ultima_cotacao'])}")
    if f["data_oficial"]:
        st.write(f"Data da promoção: {data_br(f['data_oficial'])}")
    if f["motivo_descarte"]:
        st.write(f"Último motivo de descarte ou pausa: {f['motivo_descarte']}")
    with st.expander("Editar condições e verificações"):
        formulario_fornecedor(f)
    with st.form(f"etapa_{escolhido}"):
        opcoes = [e for e in ETAPAS if e != "Fornecedor oficial"]
        etapa = st.selectbox("Etapa de acompanhamento", opcoes,
                             index=opcoes.index(f["status"]) if f["status"] in opcoes else 0)
        motivo = st.text_input("Motivo para descartar ou pausar")
        mudar = st.form_submit_button("Alterar etapa")
    if mudar:
        executar(lambda: alterar_etapa(escolhido, etapa, motivo), "Etapa atualizada.")
    st.subheader("SKUs cotados")
    config = obter_configuracao()
    tabela_skus(listar_skus(fornecedor_id=escolhido), config)
    st.caption("Para lançar ou renovar cotações, use Produtos e SKUs.")
    st.subheader("Checklist de promoção")
    st.caption(f"Exige margem de pelo menos {percentual(max(Decimal('0.20'), config.parametros.margem_alvo_pct))} em três produtos distintos.")
    checklist = avaliar_promocao(escolhido)
    for nome, ok in checklist.items():
        st.write(f"{'✅' if ok else '⬜'} {nome}")
    if st.button("Promover a fornecedor oficial"):
        pendencias = promover(escolhido)
        if pendencias:
            st.error("Promoção não realizada. Falta cumprir:")
            for pendencia in pendencias:
                st.write(f"• {pendencia}")
        else:
            st.session_state["mensagem"] = "Fornecedor promovido a oficial."
            st.rerun()
    st.subheader("Histórico de contatos")
    contatos = listar_interacoes(escolhido)
    if contatos:
        st.dataframe([{"Data": data_br(r["data"]), "Canal": r["canal"], "Resumo": r["resumo"], "Resposta": {None: "Não informada", "aguardando": "Aguardando", "recebida": "Recebida"}[r["situacao_resposta"]]}
                      for r in contatos], hide_index=True, width="stretch")
    else:
        st.info("Nenhum contato registrado.")
    with st.form(f"contato_{escolhido}"):
        data = st.date_input("Data do contato", value=date.today(), max_value=date.today())
        canal = st.text_input("Canal")
        resumo = st.text_area("Resumo do contato")
        situacao = st.selectbox("Situação da resposta", [None, "aguardando", "recebida"],
            format_func=lambda s: {None: "Não informar", "aguardando": "Aguardando resposta", "recebida": "Resposta recebida"}[s])
        adicionar = st.form_submit_button("Adicionar contato")
    if adicionar:
        executar(lambda: registrar_interacao(escolhido, data, canal, resumo, situacao_resposta=situacao), "Contato registrado.")
