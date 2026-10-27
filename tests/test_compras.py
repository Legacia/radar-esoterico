from dataclasses import replace
from decimal import Decimal as D

import pytest

from radar.banco import conectar
from radar.compras import (avaliar_lote, criterios_compra, obter_orcamento, remover_plano, salvar_orcamento, salvar_plano)
from radar.margem.configuracao import obter_configuracao, salvar_configuracao
from radar.produtos import salvar_produto
from tests.apoio_bloco3 import criar_base


def plano(db,produto,cotacao,quantidade=5,**kwargs):
    dados = dict(demanda=True,justificativa_demanda="Procura fictícia verificável",
                 concorrencia=True,justificativa_concorrencia="Comparação fictícia de preços")
    dados.update(kwargs)
    salvar_plano(produto,cotacao,quantidade,D("59.90"),caminho=db,**dados)


def test_pronto_so_com_seis_criterios(db):
    _,produto,cotacao = criar_base(db)
    plano(db,produto,cotacao)
    lote = avaliar_lote(db)
    item = lote["itens"][0]
    assert set(item["criterios"]) == {"Fornecedor","Produto","Margem","Demanda","Concorrência","Estoque"}
    assert item["pronto"]
    assert lote["comprometido_centavos"] == 10000
    assert lote["disponivel_centavos"] == 90000


@pytest.mark.parametrize("campo,valor,criterio", [("cnpj_verificado",0,"Fornecedor"),
    ("condicoes_verificadas",0,"Fornecedor"),("emite_nota",0,"Fornecedor"),
    ("status_fornecedor","Descartado ou pausado","Fornecedor"),
    ("qualidade_conferida",0,"Produto"),("procedencia_conferida",0,"Produto"),
    ("especificacoes_conferidas",0,"Produto"),("preco_venda_centavos",3000,"Margem"),
    ("demanda_confirmada",0,"Demanda"),("concorrencia_confirmada",0,"Concorrência"),
    ("justificativa_demanda"," ","Demanda"),("justificativa_concorrencia"," ","Concorrência"),
    ("quantidade_minima",10,"Estoque")])
def test_cada_criterio_pode_bloquear(db,campo,valor,criterio):
    _,produto,cotacao = criar_base(db)
    plano(db,produto,cotacao)
    item = dict(avaliar_lote(db)["itens"][0],**{campo:valor})
    resultado = criterios_compra(item,obter_configuracao(db).parametros,10000,100000,0)
    assert not resultado["criterios"][criterio]
    assert not resultado["pronto"]


@pytest.mark.parametrize("quantidade,validado,excede,pronto", [(10,False,False,True),
    (11,False,True,False),(11,True,False,True)])
def test_regra_vinte_porcento(db,quantidade,validado,excede,pronto):
    _,produto,cotacao = criar_base(db)
    plano(db,produto,cotacao,quantidade,validado=validado,justificativa_validacao="Validação fictícia" if validado else "")
    item = avaliar_lote(db)["itens"][0]
    assert item["acima_vinte"] is excede
    assert item["pronto"] is pronto


def test_reserva_preservada_e_excesso_bloqueia(db):
    _,produto,cotacao = criar_base(db)
    plano(db,produto,cotacao)
    salvar_orcamento(D(1000),D(900),db)
    assert avaliar_lote(db)["itens"][0]["pronto"]
    salvar_orcamento(D(1000),D(901),db)
    lote = avaliar_lote(db)
    assert lote["excede_disponivel"]
    assert lote["disponivel_centavos"] == -100
    assert not lote["itens"][0]["criterios"]["Estoque"]


@pytest.mark.parametrize("total,reserva", [(D(0),D(0)),(D(100),D(101)),(D(100),D(-1))])
def test_orcamento_invalido(db,total,reserva):
    with pytest.raises(ValueError):
        salvar_orcamento(total,reserva,db)


@pytest.mark.parametrize("campo", ["demanda","concorrencia","validado"])
def test_confirmacao_manual_exige_justificativa(db,campo):
    _,produto,cotacao = criar_base(db)
    with pytest.raises(ValueError,match="justificativa"):
        salvar_plano(produto,cotacao,1,D(60),caminho=db,**{campo:True})
    assert avaliar_lote(db)["itens"] == []


def test_nao_permite_cotacao_de_outro_produto(db):
    _,_,cotacao = criar_base(db)
    outro = salvar_produto("Outro fictício","","Candidato",caminho=db)
    with pytest.raises(ValueError):
        salvar_plano(outro,cotacao,1,D(60),caminho=db)


def test_trocar_alvo_reavalia_plano(db):
    _,produto,cotacao = criar_base(db)
    plano(db,produto,cotacao)
    p = replace(obter_configuracao(db).parametros,margem_alvo_pct=D("0.30"))
    salvar_configuracao(p,15,db)
    assert not avaliar_lote(db)["itens"][0]["criterios"]["Margem"]
    salvar_configuracao(replace(p,margem_alvo_pct=D("0.10")),15,db)
    assert avaliar_lote(db)["itens"][0]["pronto"]


def test_editar_nao_duplica_e_retirar_libera_orcamento(db):
    _,produto,cotacao = criar_base(db)
    plano(db,produto,cotacao)
    plano(db,produto,cotacao,10)
    assert len(avaliar_lote(db)["itens"]) == 1
    assert avaliar_lote(db)["comprometido_centavos"] == 20000
    remover_plano(produto,db)
    assert avaliar_lote(db)["comprometido_centavos"] == 0


def test_reavaliar_usa_verificacoes_atuais(db):
    fornecedor,produto,cotacao = criar_base(db)
    plano(db,produto,cotacao)
    with conectar(db) as c:
        c.execute("UPDATE fornecedor SET emite_nota=0 WHERE id=?",(fornecedor,))
    assert not avaliar_lote(db)["itens"][0]["criterios"]["Fornecedor"]
