import streamlit as st

from app.acesso import exigir_login


def mostrar():
    exigir_login()
    st.title("Painel")
    st.caption("Radar Esotérico · Tenda da Bruxa 2.0")
    st.info("A base está pronta. Os indicadores serão adicionados no Bloco 3.")
