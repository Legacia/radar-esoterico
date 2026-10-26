"""Barreira compartilhada por todas as páginas."""
import streamlit as st

from radar.sessoes import criar_sessao, usuario_da_sessao
from radar.usuarios import autenticar


def exigir_login():
    usuario = usuario_da_sessao(st.session_state.get("sessao"))
    if usuario is not None:
        return usuario
    expirada = st.session_state.pop("sessao", None) is not None
    st.title("Radar Esotérico")
    if expirada:
        st.info("Sua sessão terminou. Entre novamente.")
    st.subheader("Entrar")
    with st.form("login"):
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar")
    if entrar:
        usuario = autenticar(email, senha)
        if usuario is None:
            st.error("E-mail ou senha inválidos.")
        else:
            st.session_state["sessao"] = criar_sessao(usuario)
            st.rerun()
    st.stop()


def mostrar_saida(usuario):
    st.sidebar.write(f"Conectado: {usuario['nome']}")
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()
