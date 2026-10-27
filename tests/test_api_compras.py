from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
import pytest

from radar.api import criar_app
from radar.fornecedores import salvar_fornecedor
from radar.produtos import registrar_cotacao, salvar_produto

EMAIL, SENHA = "teste@example.invalid", "senha-ficticia-123"


@pytest.fixture
def cliente(db, conta):
    with TestClient(criar_app()) as c:
        c.post("/api/entrar", json={"email": EMAIL, "senha": SENHA})
        yield c


@pytest.fixture
def base(db):
    f = salvar_fornecedor("Fornecedor fictício", "00.000.000/0001-00", "", Decimal(0), "7 dias", "Pix",
                          True, True, True, True, True, caminho=db)
    p = salvar_produto("Kit fictício", "", "Candidato", True, True, True, caminho=db)
    cot = registrar_cotacao(f, p, "KIT", Decimal("20.00"), 5, date.today(), Decimal("59.90"), db)
    return {"produto": p, "cotacao": cot, "db": db}


def planejar(cliente, base, **campos):
    dados = {"cotacao_id": base["cotacao"], "quantidade": 5, "preco_venda": "59,90",
             "demanda": True, "justificativa_demanda": "Busca fictícia em alta",
             "concorrencia": True, "justificativa_concorrencia": "Preços fictícios parecidos", **campos}
    return cliente.put(f"/api/compras/plano/{base['produto']}", json=dados)


def test_item_pronto_com_seis_criterios_e_caso_da_margem(cliente, base):
    assert planejar(cliente, base).status_code == 200
    r = cliente.get("/api/compras").json()
    item = r["itens"][0]
    assert [c["nome"] for c in item["criterios"]] == ["Fornecedor", "Produto", "Margem", "Demanda", "Concorrência", "Estoque"]
    assert item["pronto"] is True and all(c["cumprido"] for c in item["criterios"])
    assert Decimal(item["contribuicao"]) == Decimal("14.33")
    assert round(Decimal(item["margem_pct"]), 3) == Decimal("0.239")
    assert item["valor_centavos"] == 10000 and Decimal(item["percentual_orcamento"]) == Decimal("0.1")
    assert r["comprometido_centavos"] == 10000 and r["uso_pct"] == 10


def test_nao_validado_acima_de_20_por_cento_do_orcamento_nao_fica_pronto(cliente, base):
    planejar(cliente, base, quantidade=11)  # 11 x R$ 20,00 = R$ 220,00 > 20% de R$ 1.000,00
    item = cliente.get("/api/compras").json()["itens"][0]
    assert item["acima_vinte"] is True and item["pronto"] is False
    assert {c["nome"]: c["cumprido"] for c in item["criterios"]}["Estoque"] is False
    planejar(cliente, base, quantidade=11, validado=True, justificativa_validacao="Venda teste fictícia aprovada")
    item = cliente.get("/api/compras").json()["itens"][0]
    assert item["acima_vinte"] is False and item["pronto"] is True and item["validado"] == 1


def test_margem_exige_piso_de_20_mesmo_com_alvo_menor(cliente, base):
    padrao = {"comissao": "20", "tributo": "6", "tarifa_fixa": "4,50", "embalagem": "2,50", "outros": "3,00",
              "limite_cotacao_dias": 15}
    cliente.put("/api/configuracao", json={**padrao, "margem_alvo": "10"})
    planejar(cliente, base, preco_venda="50,00")  # margem de ~14%: passa no alvo de 10%, não no piso de 20%
    margem = {c["nome"]: c["cumprido"] for c in cliente.get("/api/compras").json()["itens"][0]["criterios"]}["Margem"]
    assert margem is False


def test_orcamento_reserva_e_excesso(cliente, base):
    assert cliente.put("/api/compras/orcamento", json={"total": "1.000,00", "reserva": "950,00"}).status_code == 200
    planejar(cliente, base)
    r = cliente.get("/api/compras").json()
    assert r["orcamento"] == {"total_centavos": 100000, "reserva_centavos": 95000}
    assert r["campos_orcamento"] == {"total": "1000,00", "reserva": "950,00"}
    assert r["excede_disponivel"] is True and r["disponivel_centavos"] == -5000 and r["uso_pct"] == 100


def test_retirar_do_plano(cliente, base):
    planejar(cliente, base)
    assert cliente.delete(f"/api/compras/plano/{base['produto']}").status_code == 200
    assert cliente.get("/api/compras").json()["itens"] == []


@pytest.mark.parametrize("campos, mensagem", [
    ({"quantidade": 0}, "inteiro positivo"),
    ({"quantidade": "5"}, "formato inválido"),
    ({"preco_venda": "0"}, "preço conservador deve ser positivo"),
    ({"demanda": True, "justificativa_demanda": " "}, "justificativa de demanda"),
    ({"validado": True, "justificativa_validacao": ""}, "justificativa de validação"),
    ({"cotacao_id": 999}, "cotação deve pertencer"),
])
def test_plano_invalido_explica(cliente, base, campos, mensagem):
    r = planejar(cliente, base, **campos)
    assert r.status_code == 400 and mensagem in r.json()["detail"]
    assert cliente.get("/api/compras").json()["itens"] == []


@pytest.mark.parametrize("dados", [{"total": "0", "reserva": "0"}, {"total": "100", "reserva": "200"}, {"total": "abc", "reserva": "0"}])
def test_orcamento_invalido(cliente, dados):
    r = cliente.put("/api/compras/orcamento", json=dados)
    assert r.status_code == 400
    assert cliente.get("/api/compras").json()["orcamento"]["total_centavos"] == 100000
