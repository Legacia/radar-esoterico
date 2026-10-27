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
from app.componentes import aplicar_estilo
from app.navegacao import PAGINAS
from app.painel import mostrar
from app.fornecedores import mostrar as mostrar_fornecedores
from app.catalogo import mostrar as mostrar_catalogo
from app.calculadora import mostrar as mostrar_calculadora
from app.pesquisa import mostrar as mostrar_pesquisa
from app.importar import mostrar as mostrar_importacao
from app.compras import mostrar as mostrar_compras
from app.kits import mostrar as mostrar_kits

st.set_page_config(page_title="Radar Esotérico", page_icon="🔮", layout="wide")
aplicar_estilo()
inicializar()
usuario = exigir_login()
mostrar_saida(usuario)
paginas = {
    "painel": st.Page(mostrar, title="Painel", icon=":material/dashboard:", default=True),
    "fornecedores": st.Page(mostrar_fornecedores, title="Fornecedores", url_path="fornecedores", icon=":material/storefront:"),
    "produtos": st.Page(mostrar_catalogo, title="Produtos e SKUs", url_path="produtos", icon=":material/inventory_2:"),
    "kits": st.Page(mostrar_kits, title="Kits", url_path="kits", icon=":material/category:"),
    "pesquisa": st.Page(mostrar_pesquisa, title="Pesquisa de oportunidades", url_path="pesquisa", icon=":material/travel_explore:"),
    "importar": st.Page(mostrar_importacao, title="Importar CSV", url_path="importar", icon=":material/upload_file:"),
    "calculadora": st.Page(mostrar_calculadora, title="Calculadora e parâmetros", url_path="calculadora", icon=":material/calculate:"),
    "compras": st.Page(mostrar_compras, title="Decisão de compra", url_path="compras", icon=":material/fact_check:"),
}
PAGINAS.update(paginas)
pagina = st.navigation({
    "Visão geral": [paginas["painel"]],
    "Fornecimento": [paginas["fornecedores"], paginas["produtos"], paginas["kits"]],
    "Mercado": [paginas["pesquisa"], paginas["importar"]],
    "Decisão": [paginas["calculadora"], paginas["compras"]],
})
pagina.run()
