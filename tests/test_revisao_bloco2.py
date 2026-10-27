"""Regras da promoção decididas pelo Legacia em 26/10/2026 (ver AGENTS.md, "Ciclo do fornecedor")."""
from datetime import date
from decimal import Decimal as D

import pytest

from radar.fornecedores import avaliar_promocao, obter_fornecedor, promover, salvar_fornecedor
from radar.produtos import listar_skus, registrar_cotacao, salvar_produto

MARGEM = "Margem no alvo em pelo menos três produtos distintos"


@pytest.fixture
def fornecedor(db):
    return salvar_fornecedor("Fornecedor fictício", "CNPJ fictício", "", D(0), "5 dias", "Pix",
                             True, True, True, True, True, caminho=db)


def produtos(db, quantidade):
    return [salvar_produto(f"Produto fictício {n}", "", "Candidato", caminho=db) for n in range(quantidade)]


def cotar(fornecedor, produto, codigo, db, preco=D("59.90"), data=None):
    registrar_cotacao(fornecedor, produto, codigo, D(20), 1, data or date.today(), preco, db)


def test_um_produto_com_tres_codigos_nao_promove(fornecedor, db):
    (produto,) = produtos(db, 1)
    for codigo in ["INC-1", "INC-2", "INC-1 caixa"]:
        cotar(fornecedor, produto, codigo, db)
    assert len(listar_skus(fornecedor_id=fornecedor, caminho=db)) == 3
    assert not avaliar_promocao(fornecedor, db)[MARGEM]
    assert promover(fornecedor, db) == [MARGEM]
    assert obter_fornecedor(fornecedor, db)["status"] == "Descoberto"


def test_dois_produtos_mais_codigo_repetido_nao_promove(fornecedor, db):
    a, b = produtos(db, 2)
    cotar(fornecedor, a, "A-1", db)
    cotar(fornecedor, a, "A-2", db)
    cotar(fornecedor, b, "B-1", db)
    assert promover(fornecedor, db) == [MARGEM]


def test_tres_produtos_promovem(fornecedor, db):
    for n, produto in enumerate(produtos(db, 3)):
        cotar(fornecedor, produto, f"COD-{n}", db)
    assert promover(fornecedor, db) == []
    assert obter_fornecedor(fornecedor, db)["status"] == "Fornecedor oficial"


def test_produto_conta_pela_melhor_margem_entre_seus_codigos(fornecedor, db):
    a, b, c = produtos(db, 3)
    cotar(fornecedor, a, "A-RUIM", db, preco=D("30.00"))  # margem negativa
    cotar(fornecedor, a, "A-BOM", db)
    cotar(fornecedor, b, "B-1", db)
    cotar(fornecedor, c, "C-1", db)
    assert promover(fornecedor, db) == []


def test_produto_com_todos_os_codigos_abaixo_do_alvo_nao_conta(fornecedor, db):
    a, b, c = produtos(db, 3)
    cotar(fornecedor, a, "A-1", db, preco=D("30.00"))
    cotar(fornecedor, a, "A-2", db, preco=None)
    cotar(fornecedor, b, "B-1", db)
    cotar(fornecedor, c, "C-1", db)
    assert promover(fornecedor, db) == [MARGEM]


def test_codigo_sem_diferenciar_maiusculas_e_recotacao(fornecedor, db):
    (produto,) = produtos(db, 1)
    cotar(fornecedor, produto, "INC-1", db, preco=D("59.90"))
    cotar(fornecedor, produto, "inc-1", db, preco=D("70.00"))
    skus = listar_skus(fornecedor_id=fornecedor, caminho=db)
    assert len(skus) == 1
    assert skus[0]["codigo"] == "INC-1"  # mantém a grafia registrada primeiro
    assert skus[0]["preco_venda_centavos"] == 7000


def test_codigo_em_minusculas_nao_pode_mudar_de_produto(fornecedor, db):
    a, b = produtos(db, 2)
    cotar(fornecedor, a, "INC-1", db)
    with pytest.raises(ValueError, match="outro produto"):
        cotar(fornecedor, b, "inc-1", db)


def test_mesmo_codigo_em_fornecedores_diferentes_continua_permitido(fornecedor, db):
    outro = salvar_fornecedor("Outro fictício", "", "", D(0), "", "", caminho=db)
    a, b = produtos(db, 2)
    cotar(fornecedor, a, "ABC", db)
    cotar(outro, b, "abc", db)
    assert len(listar_skus(caminho=db)) == 2


def test_cotacao_antiga_so_avisa_e_nao_impede_promocao(fornecedor, db):
    for n, produto in enumerate(produtos(db, 3)):
        cotar(fornecedor, produto, f"COD-{n}", db, data=date(2024, 1, 1))
    assert promover(fornecedor, db) == []
