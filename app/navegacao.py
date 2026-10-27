"""Registro das páginas, preenchido por app/main.py, para links entre telas."""
import streamlit as st

PAGINAS = {}


def link(chave, rotulo, icone=None):
    """Link para outra tela; some em testes de página isolada, sem navegação."""
    if pagina := PAGINAS.get(chave):
        st.page_link(pagina, label=rotulo, icon=icone)
