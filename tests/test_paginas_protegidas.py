"""Toda página registrada em st.navigation, em app/main.py, deve exigir login sozinha.

As páginas são descobertas no código de app/main.py; uma tela nova entra no teste
automaticamente, sem precisar escrever um teste para ela.
"""
import ast
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parents[1]
MAIN = RAIZ / "app" / "main.py"


def paginas_registradas():
    arvore = ast.parse(MAIN.read_text(encoding="utf-8"))
    importados = {}
    for no in ast.walk(arvore):
        if isinstance(no, ast.ImportFrom) and no.module and no.module.startswith("app."):
            for nome in no.names:
                importados[nome.asname or nome.name] = (no.module, nome.name)
    paginas = []
    for no in ast.walk(arvore):
        if not (isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute) and no.func.attr == "Page"):
            continue
        alvo = no.args[0] if no.args else next(k.value for k in no.keywords if k.arg == "page")
        if isinstance(alvo, ast.Constant) and isinstance(alvo.value, str):
            paginas.append(("arquivo", alvo.value))
        elif isinstance(alvo, ast.Name) and alvo.id in importados:
            paginas.append(("funcao", importados[alvo.id]))
        else:
            pytest.fail(f"Página de forma não reconhecida em app/main.py, linha {no.lineno}; ajuste este teste.")
    return paginas


PAGINAS = paginas_registradas()


def test_encontra_as_paginas():
    assert PAGINAS, "Nenhuma página encontrada em st.navigation de app/main.py."


@pytest.mark.parametrize("tipo,alvo", PAGINAS, ids=str)
def test_pagina_sem_login_mostra_apenas_tela_de_entrada(db, tipo, alvo):
    if tipo == "arquivo":
        app = AppTest.from_file(str(RAIZ / alvo), default_timeout=15).run()
    else:
        modulo, funcao = alvo
        app = AppTest.from_string(f"from {modulo} import {funcao}; {funcao}()", default_timeout=15).run()
    assert not app.exception
    assert [t.value for t in app.title] == ["Radar Esotérico"]
    assert [c.label for c in app.text_input] == ["E-mail", "Senha"]
