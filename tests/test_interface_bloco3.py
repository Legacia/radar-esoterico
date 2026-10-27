from datetime import date
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace

from streamlit.testing.v1 import AppTest

from radar.compras import avaliar_lote
from radar.kits import consultar_kit, listar_kits
from radar.mercado import registrar_anuncio
from radar.painel import obter_painel
from radar.produtos import registrar_cotacao
from tests.apoio_bloco3 import criar_base


def pagina(modulo,conta):
    return AppTest.from_string(f'''
import streamlit as st
from radar.sessoes import criar_sessao
from {modulo} import mostrar
if "sessao" not in st.session_state:
    st.session_state["sessao"] = criar_sessao({{"id": {conta}, "nome": "Pessoa de teste"}})
mostrar()
''',default_timeout=20).run()


def campo(app,label,valor,ultimo=False):
    [c for c in app.text_input if c.label == label][-1 if ultimo else 0].set_value(valor)


def clicar(app,label,ultimo=False):
    return [b for b in app.button if b.label == label][-1 if ultimo else 0].click().run()


def test_pesquisa_troca_cotacao_e_mostra_novas_margens(conta,db):
    fornecedor,produto,cotacao = criar_base(db)
    registrar_anuncio("Mercado fictício","Anúncio fictício","https://example.invalid/a",D("59.90"),date.today(),produto,"em alta",db)
    outra = registrar_cotacao(fornecedor,produto,"OUTRA",D(25),1,date.today(),D("59.90"),db)
    app = pagina("app.pesquisa",conta)
    assert not app.exception
    [s for s in app.selectbox if s.label == "Cotação usada como custo"][0].select(cotacao).run()
    assert [m.value for m in app.metric] == ["1","R$ 59,90","R$ 55,56","1"]
    [s for s in app.selectbox if s.label == "Cotação usada como custo"][0].select(outra).run()
    assert not app.exception
    assert app.metric[2].value == "R$ 64,82"
    assert app.metric[3].value == "0"
    assert "R$ 9,33" in app.dataframe[-1].value.to_string()


def test_cadastro_manual_de_anuncio_pela_tela(conta,db):
    criar_base(db)
    app = pagina("app.pesquisa",conta)
    campo(app,"Marketplace","Mercado fictício")
    campo(app,"Título do anúncio","Anúncio fictício")
    campo(app,"URL do anúncio","https://example.invalid/manual")
    campo(app,"Preço observado (R$)","59,90")
    [s for s in app.selectbox if s.label == "Produto do anúncio"][0].select(1)
    clicar(app,"Salvar preço observado")
    assert not app.exception
    assert app.metric[0].value == "1"


def test_importacao_pela_tela_e_reimportacao(conta,db,monkeypatch):
    import streamlit as st
    conteudo = (Path(__file__).resolve().parents[1]/"exemplos/anuncios_ficticios.csv").read_bytes()
    monkeypatch.setattr(st,"file_uploader",lambda *args,**kwargs: SimpleNamespace(getvalue=lambda:conteudo))
    app = pagina("app.importar",conta)
    clicar(app,"Importar arquivo")
    assert not app.exception
    assert "Preços adicionados: 3" in app.success[0].value
    clicar(app,"Importar arquivo")
    assert not app.exception
    assert "Já existentes: 3" in app.success[0].value


def test_compra_pendente_depois_pronta_e_aviso_vinte_porcento(conta,db):
    _,produto,_ = criar_base(db)
    app = pagina("app.compras",conta)
    clicar(app,"Salvar planejamento")
    assert not app.exception
    assert not avaliar_lote(db)["itens"][0]["pronto"]
    for label in ["Demanda confirmada","Concorrência confirmada"]:
        [c for c in app.checkbox if c.label == label][0].check()
    for label in ["Justificativa de demanda","Justificativa de concorrência"]:
        [t for t in app.text_area if t.label == label][0].set_value("Evidência fictícia de teste")
    clicar(app,"Salvar planejamento")
    assert not app.exception
    assert avaliar_lote(db)["itens"][0]["pronto"]
    [n for n in app.number_input if n.label == "Quantidade planejada"][0].set_value(11)
    clicar(app,"Salvar planejamento")
    assert not app.exception
    assert any("mais de 20%" in w.value for w in app.warning)
    assert not avaliar_lote(db)["itens"][0]["pronto"]


def test_kits_pela_tela_componentes_custo_e_estoque(conta,db):
    criar_base(db)
    app = pagina("app.kits",conta)
    campo(app,"Nome do novo kit","Kit fictício de interface")
    clicar(app,"Criar kit")
    assert not app.exception
    clicar(app,"Salvar componente")
    assert not app.exception
    assert app.metric[0].value == "R$ 20,00"
    [n for n in app.number_input if n.label == "Kits planejados"][0].set_value(2)
    clicar(app,"Salvar plano do kit")
    assert not app.exception
    assert app.metric[1].value == "R$ 40,00"
    [n for n in app.number_input if n.label == "Estoque físico atual do componente"][0].set_value(1)
    clicar(app,"Atualizar estoque físico")
    assert not app.exception
    assert app.dataframe[-1].value.iloc[0]["Falta"] == 1


def test_painel_cadastra_e_conclui_tarefa(conta,db):
    app = pagina("app.painel",conta)
    assert not app.exception
    campo(app,"Título da tarefa","Tarefa fictícia de interface")
    clicar(app,"Salvar tarefa")
    assert not app.exception
    [c for c in app.checkbox if c.label == "Tarefa concluída"][-1].check()
    campo(app,"Responsável","Anna",ultimo=True)
    clicar(app,"Salvar tarefa",ultimo=True)
    assert not app.exception
    p = obter_painel(db)
    assert p["concluidas"] == 1
    assert p["tarefas"][0]["responsavel"] == "Anna"
