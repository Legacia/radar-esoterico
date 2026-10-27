from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from radar.compras import salvar_plano
from radar.fornecedores import alterar_etapa, listar_fornecedores, registrar_interacao
from radar.kits import (ajustar_estoque, calcular_necessidades, consultar_kit, necessidade_conjunta,
    planejar_kits, remover_componente, salvar_componente, salvar_kit)
from radar.margem.configuracao import obter_configuracao
from radar.painel import calcular_pendencias, obter_painel, salvar_tarefa
from radar.produtos import listar_skus, registrar_cotacao, salvar_produto
from tests.apoio_bloco3 import criar_base


def test_custo_kit_e_necessidade_por_componente(db):
    fornecedor,produto,cotacao = criar_base(db)
    suporte = salvar_produto("Suporte fictício","Acessórios","Candidato",caminho=db)
    cotacao_suporte = registrar_cotacao(fornecedor,suporte,"SUPORTE",D(5),1,date.today(),D(30),db)
    kit = salvar_kit("Kit fictício",caminho=db)
    salvar_componente(kit,produto,3,cotacao,db)
    salvar_componente(kit,suporte,1,cotacao_suporte,db)
    ajustar_estoque(produto,4,db)
    r = consultar_kit(kit,2,db)
    assert r["custo_unitario"] == D(65)
    assert r["custo_lote"] == D(130)
    linhas = {i["produto_id"]:i for i in r["componentes"]}
    assert (linhas[produto]["necessario"],linhas[produto]["falta"]) == (6,2)
    assert linhas[suporte]["falta"] == 2


def test_kits_compartilham_estoque_sem_contar_duas_vezes(db):
    _,produto,cotacao = criar_base(db)
    for nome,quantidade in [("Kit fictício A",2),("Kit fictício B",3)]:
        kit = salvar_kit(nome,caminho=db)
        salvar_componente(kit,produto,quantidade,cotacao,db)
        planejar_kits(kit,2,db)
    ajustar_estoque(produto,6,db)
    assert necessidade_conjunta(db) == [{"produto":"Produto fictício A","estoque":6,"necessario":10,"falta":4}]


def test_atualizar_componente_nao_duplica_e_remover_funciona(db):
    _,produto,cotacao = criar_base(db)
    kit = salvar_kit("Kit fictício",caminho=db)
    salvar_componente(kit,produto,1,cotacao,db)
    salvar_componente(kit,produto,2,cotacao,db)
    assert len(consultar_kit(kit,caminho=db)["componentes"]) == 1
    assert consultar_kit(kit,caminho=db)["custo_unitario"] == D(40)
    remover_componente(kit,produto,db)
    assert consultar_kit(kit,caminho=db)["custo_unitario"] is None


def test_componente_sem_cotacao_nao_inventa_custo():
    r = calcular_necessidades([{"quantidade":2,"estoque_atual":1,"custo_unitario_centavos":None}],3)
    assert r["custo_unitario"] is None
    assert r["componentes"][0]["falta"] == 5


@pytest.mark.parametrize("quantidade", [0,-1,1.5,True])
def test_quantidade_kit_invalida(quantidade):
    with pytest.raises(ValueError):
        calcular_necessidades([],quantidade)


def test_cotacao_de_outro_componente_recusada(db):
    _,_,cotacao = criar_base(db)
    outro = salvar_produto("Outro fictício","","Candidato",caminho=db)
    kit = salvar_kit("Kit fictício",caminho=db)
    with pytest.raises(ValueError):
        salvar_componente(kit,outro,1,cotacao,db)


@pytest.mark.parametrize("valor", [-1,1.5,True])
def test_estoque_invalido(db,valor):
    _,produto,_ = criar_base(db)
    with pytest.raises(ValueError):
        ajustar_estoque(produto,valor,db)


def test_pendencias_usam_datas_etapas_e_resposta_explicita(db):
    fornecedor,produto,_ = criar_base(db)
    hoje = date.today()
    alterar_etapa(fornecedor,"Em contato",caminho=db)
    registrar_interacao(fornecedor,hoje-timedelta(days=6),"Telefone","Contato fictício",db,situacao_resposta="aguardando")
    registrar_cotacao(fornecedor,produto,"ANTIGO",D(40),1,hoje-timedelta(days=16),D(50),db)
    painel = obter_painel(db,hoje)
    tipos = {p["tipo"] for p in painel["pendencias"]}
    assert tipos == {"Sem resposta há mais de 5 dias","Cotação antiga","Margem abaixo do alvo"}
    assert all(p["responsavel"] == "Legacia" for p in painel["pendencias"])
    registrar_interacao(fornecedor,hoje,"Telefone","Resposta fictícia",db,situacao_resposta="recebida")
    assert not any(p["tipo"].startswith("Sem resposta") for p in obter_painel(db,hoje)["pendencias"])


def test_contato_neutro_nao_reinicia_espera_e_cinco_dias_nao_atrasa(db):
    fornecedor,_,_ = criar_base(db)
    hoje = date.today()
    alterar_etapa(fornecedor,"Em contato",caminho=db)
    registrar_interacao(fornecedor,hoje-timedelta(days=5),"Telefone","Contato fictício",db,situacao_resposta="aguardando")
    registrar_interacao(fornecedor,hoje,"Anotação","Observação fictícia",db)
    assert not obter_painel(db,hoje)["pendencias"]
    assert any(p["tipo"].startswith("Sem resposta") for p in obter_painel(db,hoje+timedelta(days=1))["pendencias"])


def test_contatos_antigos_sem_classificacao_nao_sao_presumidos_sem_resposta(db):
    fornecedor,_,_ = criar_base(db)
    alterar_etapa(fornecedor,"Em contato",caminho=db)
    registrar_interacao(fornecedor,date.today()-timedelta(days=10),"Telefone","Sem classificação",db)
    assert obter_painel(db)["pendencias"] == []


def test_amostra_pendente_somente_em_avaliacao_e_sugere_anna(db):
    fornecedor,_,_ = criar_base(db)
    fornecedores = listar_fornecedores(db)
    fornecedores[0]["amostra_avaliada"] = 0
    config = obter_configuracao(db)
    assert calcular_pendencias(fornecedores,[],[],config.parametros,15,date.today()) == []
    fornecedores[0]["status"] = "Em avaliação"
    r = calcular_pendencias(fornecedores,[],[],config.parametros,15,date.today())
    assert len(r) == 1 and r[0]["responsavel"] == "Anna"
    fornecedores[0]["status"] = "Descartado ou pausado"
    assert calcular_pendencias(fornecedores,listar_skus(caminho=db),[],config.parametros,15,date.today()) == []


def test_painel_conta_prontos_comprometido_funil_e_tarefas(db):
    _,produto,cotacao = criar_base(db)
    salvar_plano(produto,cotacao,5,D("59.90"),True,"Demanda fictícia",True,"Concorrência fictícia",caminho=db)
    tarefa = salvar_tarefa("Tarefa fictícia",1,"Legacia",caminho=db)
    salvar_tarefa("Tarefa fictícia revisada",2,"Anna",True,tarefa,db)
    p = obter_painel(db)
    assert (p["fornecedores_ativos"],p["candidatos"],p["prontos"],p["comprometido_centavos"]) == (1,1,1,10000)
    assert p["concluidas"] == 1
    assert len(p["tarefas"]) == 1
    assert p["tarefas"][0]["responsavel"] == "Anna"
    assert sum(e["quantidade"] for e in p["funil"]) == 1


@pytest.mark.parametrize("semana", [0,5,1.5])
def test_semana_tarefa_invalida(db,semana):
    with pytest.raises(ValueError):
        salvar_tarefa("Fictícia",semana,"Anna",caminho=db)
