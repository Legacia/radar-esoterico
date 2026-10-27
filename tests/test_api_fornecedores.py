from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
import pytest

from radar.api import criar_app
from radar.fornecedores import alterar_etapa, salvar_fornecedor
from radar.produtos import registrar_cotacao, salvar_produto

EMAIL, SENHA = "teste@example.invalid", "senha-ficticia-123"


@pytest.fixture
def cliente(db, conta):
    with TestClient(criar_app()) as c:
        c.post("/api/entrar", json={"email": EMAIL, "senha": SENHA})
        yield c


def novo(cliente, **campos):
    dados = {"nome": "Fornecedor fictício", **campos}
    resposta = cliente.post("/api/fornecedores", json=dados)
    assert resposta.status_code == 200, resposta.json()
    return resposta.json()["id"]


def apto(db):
    """Fornecedor fictício com tudo verificado e três produtos com margem de 23,9%."""
    f = salvar_fornecedor("Fornecedor fictício Alfa", "00.000.000/0001-00", "Contato fictício", Decimal(300),
                          "7 dias", "Pix", True, True, True, True, True, caminho=db)
    for n in range(3):
        p = salvar_produto(f"Produto fictício {n}", "Incensos", "Candidato", caminho=db)
        registrar_cotacao(f, p, f"COD-{n}", Decimal("20.00"), 10, date.today(), Decimal("59.90"), db)
    alterar_etapa(f, "Em avaliação", caminho=db)
    return f


def test_cadastra_e_lista_com_etapas(cliente):
    f = novo(cliente, pedido_minimo="1.234,56", prazo="7 dias")
    r = cliente.get("/api/fornecedores").json()
    assert r["etapas"][0] == "Descoberto" and r["etapas"][-1] == "Descartado ou pausado"
    assert r["fornecedores"] == [{"id": f, "nome": "Fornecedor fictício", "status": "Descoberto",
        "prazo": "7 dias", "condicao_pagamento": "", "data_ultima_cotacao": None}]
    assert cliente.get(f"/api/fornecedores/{f}").json()["pedido_minimo_centavos"] == 123456


@pytest.mark.parametrize("valor", ["300", "300,00", "300.00"])
def test_pedido_minimo_aceita_formatos_e_vira_centavos(cliente, valor):
    f = novo(cliente, pedido_minimo=valor)
    assert cliente.get(f"/api/fornecedores/{f}").json()["pedido_minimo_centavos"] == 30000


@pytest.mark.parametrize("campos, mensagem", [
    ({"nome": " "}, "Informe o nome do fornecedor."),
    ({"pedido_minimo": "12,345"}, "no máximo duas casas"),
    ({"pedido_minimo": "abc"}, "Informe um número"),
    ({"cnpj_verificado": True}, "Informe o CNPJ antes"),
    ({"condicoes_verificadas": True, "prazo": "7 dias"}, "Informe prazo e pagamento"),
    ({"emite_nota": "sim"}, "formato inválido"),
])
def test_cadastro_invalido_explica(cliente, campos, mensagem):
    resposta = cliente.post("/api/fornecedores", json={"nome": "Fornecedor fictício", **campos})
    assert resposta.status_code == 400
    assert mensagem in resposta.json()["detail"]


def test_ficha_traz_checklist_skus_e_margem_da_regra(cliente, db):
    f = apto(db)
    r = cliente.get(f"/api/fornecedores/{f}").json()
    assert all(item["cumprido"] for item in r["checklist"])
    assert len(r["checklist"]) == 7
    assert Decimal(r["margem_minima_pct"]) == Decimal("0.20")
    sku = r["skus"][0]
    # Caso obrigatório da margem: R$ 59,90 e custo R$ 20,00.
    assert Decimal(sku["contribuicao"]) == Decimal("14.33")
    assert round(Decimal(sku["margem_pct"]), 3) == Decimal("0.239")
    assert sku["preco_minimo"] == "55.56"
    assert sku["custo_centavos"] == 2000 and sku["cotacao_antiga"] is False


def test_cotacao_antiga_e_sem_preco_conservador(cliente, db):
    f = salvar_fornecedor("Fornecedor fictício Beta", "", "", Decimal(0), "", "", caminho=db)
    p = salvar_produto("Produto fictício", "", "Candidato", caminho=db)
    registrar_cotacao(f, p, "X", Decimal("5.00"), 1, date.today() - timedelta(days=60), None, db)
    sku = cliente.get(f"/api/fornecedores/{f}").json()["skus"][0]
    assert sku["cotacao_antiga"] is True
    assert sku["contribuicao"] is None and sku["margem_pct"] is None


def test_promover_so_com_checklist_completo(cliente, db):
    f = novo(cliente)
    r = cliente.post(f"/api/fornecedores/{f}/promover").json()
    assert r["promovido"] is False and "Emite nota fiscal" in r["pendencias"]
    assert cliente.get(f"/api/fornecedores/{f}").json()["status"] == "Descoberto"
    g = apto(db)
    assert cliente.post(f"/api/fornecedores/{g}/promover").json() == {"promovido": True, "pendencias": []}
    ficha = cliente.get(f"/api/fornecedores/{g}").json()
    assert ficha["status"] == "Fornecedor oficial" and ficha["data_oficial"] == date.today().isoformat()


def test_etapa_exige_motivo_e_nao_promove(cliente):
    f = novo(cliente)
    assert cliente.post(f"/api/fornecedores/{f}/etapa", json={"etapa": "Em contato"}).status_code == 200
    sem_motivo = cliente.post(f"/api/fornecedores/{f}/etapa", json={"etapa": "Descartado ou pausado"})
    assert sem_motivo.status_code == 400 and "motivo" in sem_motivo.json()["detail"]
    oficial = cliente.post(f"/api/fornecedores/{f}/etapa", json={"etapa": "Fornecedor oficial"})
    assert oficial.status_code == 400
    assert cliente.post(f"/api/fornecedores/{f}/etapa", json={"etapa": "Inventada"}).status_code == 400
    ok = cliente.post(f"/api/fornecedores/{f}/etapa", json={"etapa": "Descartado ou pausado", "motivo": "Preço alto"})
    assert ok.status_code == 200
    ficha = cliente.get(f"/api/fornecedores/{f}").json()
    assert ficha["status"] == "Descartado ou pausado" and ficha["motivo_descarte"] == "Preço alto"


def test_contatos(cliente):
    f = novo(cliente)
    hoje = date.today().isoformat()
    r = cliente.post(f"/api/fornecedores/{f}/contatos",
                     json={"data": hoje, "canal": "WhatsApp", "resumo": "Pedido de catálogo", "situacao_resposta": "aguardando"})
    assert r.status_code == 200
    contatos = cliente.get(f"/api/fornecedores/{f}").json()["contatos"]
    assert contatos[0]["canal"] == "WhatsApp" and contatos[0]["situacao_resposta"] == "aguardando"
    for dados, mensagem in [
        ({"data": (date.today() + timedelta(days=1)).isoformat()}, "data futura"),
        ({"data": "27/10/2026"}, "data válida"),
        ({"canal": " "}, "canal"),
        ({"situacao_resposta": "talvez"}, "Situação da resposta inválida"),
    ]:
        resposta = cliente.post(f"/api/fornecedores/{f}/contatos",
                                json={"data": hoje, "canal": "E-mail", "resumo": "x", **dados})
        assert resposta.status_code == 400 and mensagem in resposta.json()["detail"], dados


def test_fornecedor_inexistente(cliente):
    for metodo, caminho, corpo in [("GET", "/api/fornecedores/999", None),
                                   ("PUT", "/api/fornecedores/999", {"nome": "X"}),
                                   ("POST", "/api/fornecedores/999/promover", None),
                                   ("POST", "/api/fornecedores/999/etapa", {"etapa": "Em contato"}),
                                   ("POST", "/api/fornecedores/999/contatos",
                                    {"data": date.today().isoformat(), "canal": "x", "resumo": "x"})]:
        resposta = cliente.request(metodo, caminho, json=corpo)
        assert resposta.status_code == 400 and resposta.json()["detail"] == "Fornecedor não encontrado.", caminho
