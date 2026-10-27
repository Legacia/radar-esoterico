from datetime import date
from decimal import Decimal
import streamlit as st

from app.acesso import exigir_login
from app.componentes import cabecalho, executar, mensagem, selo, tabela_skus
from app.navegacao import link
from radar.fornecedores import (ETAPAS, alterar_etapa, avaliar_promocao, listar_fornecedores,
    listar_interacoes, obter_fornecedor, promover, registrar_interacao, salvar_fornecedor)
from radar.margem.configuracao import obter_configuracao
from radar.produtos import listar_skus
from radar.valores import data_br, dinheiro_texto, percentual, reais, texto_decimal

COR_ETAPA = {"Descoberto": "gray", "Em contato": "blue", "Cotado": "violet", "Em avaliação": "orange",
             "Fornecedor oficial": "green", "Descartado ou pausado": "red"}
RESPOSTA = {None: "Não informada", "aguardando": "Aguardando", "recebida": "Recebida"}


def formulario_fornecedor(fornecedor=None):
    f = fornecedor or {}
    with st.form(f"fornecedor_{f.get('id', 'novo')}"):
        a, b = st.columns(2)
        nome = a.text_input("Nome do fornecedor", f.get("nome", ""))
        cnpj = b.text_input("CNPJ", f.get("cnpj") or "")
        contato = a.text_input("Contato", f.get("contato") or "")
        minimo = b.text_input("Pedido mínimo (R$)", texto_decimal(Decimal(f.get("pedido_minimo_centavos", 0)) / 100))
        prazo = a.text_input("Prazo", f.get("prazo") or "")
        pagamento = b.text_input("Condição de pagamento", f.get("condicao_pagamento") or "")
        st.markdown("**Verificações manuais**")
        st.caption("Confirmações feitas por vocês após verificar as informações.")
        a, b = st.columns(2)
        cnpj_ok = a.checkbox("CNPJ verificado", bool(f.get("cnpj_verificado")))
        condicoes_ok = a.checkbox("Condições comerciais verificadas", bool(f.get("condicoes_verificadas")))
        nota = a.checkbox("Emite nota fiscal", bool(f.get("emite_nota")))
        amostra = b.checkbox("Amostra avaliada pela Anna (especificações, procedência e qualidade)", bool(f.get("amostra_avaliada")))
        reposicao = b.checkbox("Reposição confirmada", bool(f.get("reposicao_confirmada")))
        salvar = st.form_submit_button("Salvar fornecedor", type="primary")
    if salvar:
        executar(lambda: salvar_fornecedor(nome, cnpj, contato, dinheiro_texto(minimo), prazo,
                pagamento, cnpj_ok, condicoes_ok, nota, amostra, reposicao,
                fornecedor_id=f.get("id")), "Fornecedor salvo.")


def visao_geral(fornecedores):
    for etapa, coluna in zip(ETAPAS, st.columns(len(ETAPAS))):
        coluna.metric(etapa, sum(f["status"] == etapa for f in fornecedores))
    st.dataframe([{"Fornecedor": f["nome"], "Etapa": f["status"], "Prazo": f["prazo"] or "Não informado",
        "Pagamento": f["condicao_pagamento"] or "Não informado", "Última cotação": data_br(f["data_ultima_cotacao"])}
        for f in fornecedores], hide_index=True, width="stretch")


def cabecalho_ficha(f, checklist):
    with st.container(border=True):
        st.subheader(f["nome"])
        cumpridos = sum(checklist.values())
        st.markdown(f"{selo(f['status'], COR_ETAPA.get(f['status'], 'gray'))} "
                    f"{selo(f'{cumpridos} de {len(checklist)} itens do checklist', 'green' if all(checklist.values()) else 'orange')}")
        a, b, c, d = st.columns(4)
        a.markdown(f"**Pedido mínimo**  \n{reais(Decimal(f['pedido_minimo_centavos']) / 100)}")
        b.markdown(f"**Prazo**  \n{f['prazo'] or ':gray[Não informado]'}")
        c.markdown(f"**Pagamento**  \n{f['condicao_pagamento'] or ':gray[Não informado]'}")
        d.markdown(f"**Última cotação**  \n{data_br(f['data_ultima_cotacao'])}")
        if f["data_oficial"]:
            st.caption(f"Promovido a oficial em {data_br(f['data_oficial'])}.")
        if f["motivo_descarte"]:
            st.caption(f"Último motivo de descarte ou pausa: {f['motivo_descarte']}")


def aba_checklist(f, escolhido, checklist, config):
    st.markdown("**Checklist de promoção**")
    st.caption(f"Exige margem de pelo menos {percentual(max(Decimal('0.20'), config.parametros.margem_alvo_pct))} em três produtos distintos.")
    for nome, ok in checklist.items():
        st.markdown(f"{selo('Cumprido', 'green') if ok else selo('Pendente', 'orange')} {nome}")
    if st.button("Promover a fornecedor oficial", type="primary", icon=":material/verified:"):
        pendencias = promover(escolhido)
        if pendencias:
            st.error("Promoção não realizada. Falta cumprir:")
            for pendencia in pendencias:
                st.write(f"• {pendencia}")
        else:
            st.session_state["mensagem"] = "Fornecedor promovido a oficial."
            st.rerun()
    st.caption("O sistema nunca promove sozinho: o botão confere o checklist e só muda a etapa se tudo estiver cumprido.")
    st.divider()
    with st.form(f"etapa_{escolhido}"):
        st.markdown("**Mudar etapa de acompanhamento**")
        opcoes = [e for e in ETAPAS if e != "Fornecedor oficial"]
        a, b = st.columns(2)
        etapa = a.selectbox("Etapa de acompanhamento", opcoes,
                            index=opcoes.index(f["status"]) if f["status"] in opcoes else 0)
        motivo = b.text_input("Motivo para descartar ou pausar")
        mudar = st.form_submit_button("Alterar etapa")
    if mudar:
        executar(lambda: alterar_etapa(escolhido, etapa, motivo), "Etapa atualizada.")


def aba_contatos(escolhido):
    historico = listar_interacoes(escolhido)
    if historico:
        st.dataframe([{"Data": data_br(r["data"]), "Canal": r["canal"], "Resumo": r["resumo"],
            "Resposta": RESPOSTA[r["situacao_resposta"]]} for r in historico], hide_index=True, width="stretch")
    else:
        st.info("Nenhum contato registrado.")
    with st.form(f"contato_{escolhido}"):
        st.markdown("**Registrar contato**")
        a, b, c = st.columns(3)
        data = a.date_input("Data do contato", value=date.today(), max_value=date.today(), format="DD/MM/YYYY")
        canal = b.text_input("Canal")
        situacao = c.selectbox("Situação da resposta", [None, "aguardando", "recebida"],
            format_func=lambda s: {None: "Não informar", "aguardando": "Aguardando resposta", "recebida": "Resposta recebida"}[s])
        resumo = st.text_area("Resumo do contato")
        adicionar = st.form_submit_button("Adicionar contato", type="primary")
    if adicionar:
        executar(lambda: registrar_interacao(escolhido, data, canal, resumo, situacao_resposta=situacao), "Contato registrado.")


def mostrar():
    exigir_login()
    cabecalho("Fornecedores", "Ciclo de cada fornecedor, do primeiro contato à promoção a oficial. "
              "Promoção, descarte e pausa são sempre decisões de vocês.")
    mensagem()
    with st.expander("Cadastrar fornecedor", icon=":material/add:"):
        formulario_fornecedor()
    fornecedores = listar_fornecedores()
    if not fornecedores:
        st.info("Nenhum fornecedor cadastrado. Use \"Cadastrar fornecedor\" acima para começar.")
        return
    visao_geral(fornecedores)
    por_id = {f["id"]: f for f in fornecedores}
    escolhido = st.selectbox("Abrir ficha", list(por_id), format_func=lambda i: f"{por_id[i]['nome']} · {por_id[i]['status']}")
    f = obter_fornecedor(escolhido)
    config = obter_configuracao()
    checklist = avaliar_promocao(escolhido)
    cabecalho_ficha(f, checklist)
    resumo, condicoes, cotacoes, contatos = st.tabs(["Checklist e etapa", "Condições e verificações", "SKUs cotados", "Contatos"])
    with resumo:
        aba_checklist(f, escolhido, checklist, config)
    with condicoes:
        formulario_fornecedor(f)
    with cotacoes:
        tabela_skus(listar_skus(fornecedor_id=escolhido), config)
        link("produtos", "Lançar ou renovar cotações em Produtos e SKUs", ":material/arrow_forward:")
    with contatos:
        aba_contatos(escolhido)
