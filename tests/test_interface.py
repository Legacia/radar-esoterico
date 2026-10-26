from pathlib import Path

from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parents[1]


def abrir():
    return AppTest.from_file(str(RAIZ / "app" / "main.py"), default_timeout=15).run()


def entrar(app, email="teste@example.invalid", senha="senha-ficticia-123"):
    app.text_input[0].set_value(email)
    app.text_input[1].set_value(senha)
    return app.button[0].click().run()


def test_painel_bloqueado_sem_login(db):
    app = abrir()
    assert not app.exception
    assert app.title[0].value == "Radar Esotérico"
    assert not any(t.value == "Painel" for t in app.title)


def test_login_abre_painel_e_sair_bloqueia(conta, db):
    app = entrar(abrir())
    assert not app.exception
    assert app.title[0].value == "Painel"
    app.sidebar.button[0].click().run()
    assert not app.exception
    assert app.title[0].value == "Radar Esotérico"


def test_erro_generico_para_email_e_senha(conta, db):
    app = entrar(abrir(), senha="errada")
    erro_senha = app.error[0].value
    app = entrar(app, email="ausente@example.invalid")
    assert app.error[0].value == erro_senha == "E-mail ou senha inválidos."
    assert app.title[0].value != "Painel"


def test_sessao_expirada_bloqueia_painel(conta, db):
    app = entrar(abrir())
    sessao = dict(app.session_state["sessao"])
    sessao["inicio"] -= 8 * 3600
    app.session_state["sessao"] = sessao
    app.run()
    assert not app.exception
    assert app.title[0].value == "Radar Esotérico"
    assert app.info[0].value == "Sua sessão terminou. Entre novamente."


def test_pagina_verifica_login_diretamente(db):
    app = AppTest.from_string("from app.painel import mostrar; mostrar()", default_timeout=15).run()
    assert not app.exception
    assert app.title[0].value == "Radar Esotérico"
