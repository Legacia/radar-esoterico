from decimal import Decimal as D

from streamlit.testing.v1 import AppTest

from radar.fornecedores import obter_fornecedor
from radar.margem.configuracao import obter_configuracao
from radar.produtos import listar_produtos, listar_skus, salvar_produto


def pagina(modulo, conta):
    return AppTest.from_string(f'''
import streamlit as st
from radar.sessoes import criar_sessao
from {modulo} import mostrar
if "sessao" not in st.session_state:
    st.session_state["sessao"] = criar_sessao({{"id": {conta}, "nome": "Pessoa de teste"}})
mostrar()
''', default_timeout=15).run()


def campo(app, label, valor, *, ultimo=False):
    campos = [c for c in app.text_input if c.label == label]
    campos[-1 if ultimo else 0].set_value(valor)


def clicar(app, label, *, ultimo=False):
    botoes = [b for b in app.button if b.label == label]
    return botoes[-1 if ultimo else 0].click().run()


def test_calculadora_e_configuracao_pela_tela(conta, db):
    app = pagina("app.calculadora", conta)
    assert not app.exception
    campo(app, "Preço de venda (R$)", "59,90")
    campo(app, "Custo do produto (R$)", "20,00")
    clicar(app, "Calcular margem")
    assert not app.exception
    assert [m.value for m in app.metric] == ["R$ 14,33", "23,9%", "R$ 55,56"]
    campo(app, "Comissão (%)", "10")
    clicar(app, "Salvar parâmetros")
    assert not app.exception
    assert obter_configuracao(db).parametros.comissao_pct == D("0.10")
    campo(app, "Preço de venda (R$)", "59,90")
    campo(app, "Custo do produto (R$)", "20,00")
    clicar(app, "Calcular margem")
    assert app.metric[0].value == "R$ 20,32"


def test_calculadora_mostra_erro_de_entrada(conta, db):
    app = pagina("app.calculadora", conta)
    campo(app, "Preço de venda (R$)", "0")
    campo(app, "Custo do produto (R$)", "20")
    clicar(app, "Calcular margem")
    assert app.error
    assert not app.exception


def test_fluxo_cadastro_skus_checklist_e_promocao(conta, db):
    fornecedor = pagina("app.fornecedores", conta)
    campo(fornecedor, "Nome do fornecedor", "Fornecedor fictício de interface")
    clicar(fornecedor, "Salvar fornecedor")
    assert not fornecedor.exception
    clicar(fornecedor, "Promover a fornecedor oficial")
    assert fornecedor.error[0].value == "Promoção não realizada. Falta cumprir:"
    assert obter_fornecedor(1, db)["status"] == "Descoberto"

    campo(fornecedor, "CNPJ", "CNPJ fictício", ultimo=True)
    campo(fornecedor, "Prazo", "5 dias", ultimo=True)
    campo(fornecedor, "Condição de pagamento", "Pix", ultimo=True)
    for label in ["CNPJ verificado", "Condições comerciais verificadas", "Emite nota fiscal",
        "Amostra avaliada pela Anna (especificações, procedência e qualidade)", "Reposição confirmada"]:
        [c for c in fornecedor.checkbox if c.label == label][-1].check()
    clicar(fornecedor, "Salvar fornecedor", ultimo=True)
    assert not fornecedor.exception

    catalogo = pagina("app.catalogo", conta)
    campo(catalogo, "Nome do produto", "Produto fictício de interface")
    clicar(catalogo, "Salvar produto")
    assert not catalogo.exception
    assert len(listar_produtos(db)) == 1
    # A promoção exige três produtos diferentes; os outros dois entram direto no banco.
    for n in (2, 3):
        salvar_produto(f"Produto fictício de interface {n}", "", "Candidato", caminho=db)
    catalogo.run()
    for n, produto_id in enumerate(p["id"] for p in listar_produtos(db)):
        catalogo.selectbox[0].set_value(produto_id).run()
        campo(catalogo, "Código no fornecedor", f"FICTICIO-{n}")
        campo(catalogo, "Custo unitário (R$)", "20,00")
        campo(catalogo, "Preço conservador de venda (R$), opcional", "59,90")
        clicar(catalogo, "Salvar cotação")
        assert not catalogo.exception
    assert len(listar_skus(caminho=db)) == 3
    fornecedor.run()
    clicar(fornecedor, "Promover a fornecedor oficial")
    assert not fornecedor.exception
    assert obter_fornecedor(1, db)["status"] == "Fornecedor oficial"
    campo(fornecedor, "Canal", "Telefone")
    fornecedor.text_area[0].set_value("Contato fictício de teste")
    clicar(fornecedor, "Adicionar contato")
    assert not fornecedor.exception
    assert fornecedor.success


def test_catalogo_sem_fornecedor_orienta_cadastro(conta, db):
    app = pagina("app.catalogo", conta)
    campo(app, "Nome do produto", "Fictício")
    clicar(app, "Salvar produto")
    assert not app.exception
    assert any("Cadastre um fornecedor" in i.value for i in app.info)


def test_interface_expirada_nao_mostra_telas_novas(conta, db):
    app = pagina("app.calculadora", conta)
    sessao = dict(app.session_state["sessao"])
    sessao["inicio"] -= 8 * 3600
    app.session_state["sessao"] = sessao
    app.run()
    assert not app.exception
    assert [t.value for t in app.title] == ["Radar Esotérico"]
    assert not app.metric
