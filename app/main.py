"""Entrada: streamlit run app/main.py, a partir da raiz do projeto."""
from pathlib import Path
import sys

# O Streamlit inclui app/ no caminho; os módulos vivem na raiz do projeto.
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st

from radar.banco import inicializar
from app.acesso import exigir_login, mostrar_saida
from app.painel import mostrar

st.set_page_config(page_title="Radar Esotérico", page_icon="🔮")
inicializar()
usuario = exigir_login()
mostrar_saida(usuario)
pagina = st.navigation([st.Page(mostrar, title="Painel", default=True)])
pagina.run()
