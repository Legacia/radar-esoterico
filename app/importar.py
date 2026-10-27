import streamlit as st

from app.acesso import exigir_login
from app.componentes import cabecalho
from app.navegacao import link
from radar.importacao import importar_csv


def mostrar_relatorio(relatorio):
    st.success(f"Preços adicionados: {relatorio.importadas}. Já existentes: {relatorio.repetidas}. Linhas com erro: {len(relatorio.erros)}.")
    if relatorio.erros:
        st.dataframe([{"Linha": r["linha"], "Erro": r["erro"]} for r in relatorio.erros], hide_index=True, width="stretch")


def mostrar():
    exigir_login()
    cabecalho("Importar CSV", "Traga vários anúncios e preços observados de uma vez. Cada preço guarda a data.")
    st.write("Selecione um CSV UTF-8 separado por ponto e vírgula, com estas colunas:")
    st.code("marketplace;titulo;url;preco;data;produto;sinal", language=None)
    st.caption("Produto e sinal são opcionais. Use o nome do produto cadastrado ou deixe em branco para vincular depois na Pesquisa. Preço: 59,90; data: 2026-10-26.")
    arquivo = st.file_uploader("Arquivo CSV", type=["csv"])
    if st.button("Importar arquivo", disabled=arquivo is None, type="primary", icon=":material/upload:"):
        try:
            relatorio = importar_csv(arquivo.getvalue())
            st.session_state["relatorio_csv"] = relatorio
        except ValueError as erro:
            st.session_state.pop("relatorio_csv", None)
            st.error(str(erro))
    if relatorio := st.session_state.get("relatorio_csv"):
        st.subheader("Última importação")
        mostrar_relatorio(relatorio)
        link("pesquisa", "Vincular e analisar na Pesquisa de oportunidades", ":material/arrow_forward:")
    st.info("Reimportar a mesma observação não a duplica. Confira o relatório e corrija as linhas rejeitadas.")
