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
    f = salvar_fornecedor("Fornecedor fictício", "", "", Decimal(0), "", "", caminho=db)
    incenso = salvar_produto("Incenso fictício", "", "Candidato", caminho=db)
    suporte = salvar_produto("Suporte fictício", "", "Candidato", caminho=db)
    return {
        "incenso": incenso, "suporte": suporte,
        "cot_incenso": registrar_cotacao(f, incenso, "INC", Decimal("4.50"), 1, date.today(), None, db),
        "cot_suporte": registrar_cotacao(f, suporte, "SUP", Decimal("6.00"), 1, date.today(), None, db),
    }


def kit_com_componentes(cliente, base, planejados=0):
    k = cliente.post("/api/kits", json={"nome": "Kit fictício 3 incensos"}).json()["id"]
    assert cliente.put(f"/api/kits/{k}/componentes/{base['incenso']}",
                       json={"quantidade": 3, "cotacao_id": base["cot_incenso"]}).status_code == 200
    cliente.put(f"/api/kits/{k}/componentes/{base['suporte']}", json={"quantidade": 1, "cotacao_id": base["cot_suporte"]})
    if planejados:
        cliente.put(f"/api/kits/{k}", json={"nome": "Kit fictício 3 incensos", "quantidade_planejada": planejados})
    return k


def test_custo_do_kit_e_do_lote(cliente, base):
    k = kit_com_componentes(cliente, base, planejados=10)
    ficha = cliente.get(f"/api/kits/{k}").json()
    # 3 x 4,50 + 1 x 6,00 = 19,50 por kit; 10 kits = 195,00
    assert Decimal(ficha["custo_unitario"]) == Decimal("19.50")
    assert Decimal(ficha["custo_lote"]) == Decimal("195.00")
    assert [c["produto"] for c in ficha["componentes"]] == ["Incenso fictício", "Suporte fictício"]
    assert ficha["componentes"][0]["quantidade"] == 3 and ficha["componentes"][0]["custo_unitario_centavos"] == 450


def test_sem_plano_mostra_custo_de_um_kit_e_nenhum_lote(cliente, base):
    k = kit_com_componentes(cliente, base)
    ficha = cliente.get(f"/api/kits/{k}").json()
    assert Decimal(ficha["custo_unitario"]) == Decimal("19.50") and ficha["custo_lote"] is None


def test_necessidade_conjunta_usa_estoque_por_componente(cliente, base):
    kit_com_componentes(cliente, base, planejados=10)
    outro = cliente.post("/api/kits", json={"nome": "Kit fictício só incenso"}).json()["id"]
    cliente.put(f"/api/kits/{outro}/componentes/{base['incenso']}", json={"quantidade": 2, "cotacao_id": base["cot_incenso"]})
    cliente.put(f"/api/kits/{outro}", json={"nome": "Kit fictício só incenso", "quantidade_planejada": 5})
    assert cliente.put(f"/api/estoque/{base['incenso']}", json={"estoque": 25}).status_code == 200
    necessidade = {n["produto"]: n for n in cliente.get("/api/kits").json()["necessidade"]}
    assert necessidade["Incenso fictício"] == {"produto": "Incenso fictício", "estoque": 25, "necessario": 40, "falta": 15}
    assert necessidade["Suporte fictício"]["falta"] == 10


def test_remover_componente_e_plano_zero_sai_da_necessidade(cliente, base):
    k = kit_com_componentes(cliente, base, planejados=2)
    assert cliente.delete(f"/api/kits/{k}/componentes/{base['suporte']}").status_code == 200
    assert [c["produto"] for c in cliente.get(f"/api/kits/{k}").json()["componentes"]] == ["Incenso fictício"]
    cliente.put(f"/api/kits/{k}", json={"nome": "Kit fictício", "quantidade_planejada": 0})
    assert cliente.get("/api/kits").json()["necessidade"] == []


def test_plano_com_nome_vazio_nao_grava_nada(cliente, base):
    k = kit_com_componentes(cliente, base, planejados=2)
    r = cliente.put(f"/api/kits/{k}", json={"nome": " ", "quantidade_planejada": 9})
    assert r.status_code == 400 and r.json()["detail"] == "Informe o nome do kit."
    assert cliente.get(f"/api/kits/{k}").json()["quantidade_planejada"] == 2


@pytest.mark.parametrize("metodo, caminho, corpo, mensagem", [
    ("POST", "/api/kits", {"nome": ""}, "Informe o nome do kit."),
    ("PUT", "/api/kits/{k}", {"nome": "X", "quantidade_planejada": -1}, "inteiro não negativo"),
    ("PUT", "/api/kits/{k}", {"nome": "X", "quantidade_planejada": 1.5}, "formato inválido"),
    ("PUT", "/api/kits/{k}/componentes/{incenso}", {"quantidade": 0, "cotacao_id": "{cot_incenso}"}, "inteiro positivo"),
    ("PUT", "/api/kits/{k}/componentes/{incenso}", {"quantidade": 1, "cotacao_id": "{cot_suporte}"}, "cotação do componente"),
    ("PUT", "/api/estoque/{incenso}", {"estoque": -3}, "não negativo"),
    ("PUT", "/api/estoque/999", {"estoque": 1}, "Produto não encontrado."),
    ("GET", "/api/kits/999", None, "Kit não encontrado."),
    ("PUT", "/api/kits/999", {"nome": "X", "quantidade_planejada": 1}, "Kit não encontrado."),
])
def test_entradas_invalidas_explicam(cliente, base, metodo, caminho, corpo, mensagem):
    k = cliente.post("/api/kits", json={"nome": "Kit fictício"}).json()["id"]
    valores = {**base, "k": k}
    if corpo:
        corpo = {c: (valores[v[1:-1]] if isinstance(v, str) and v.startswith("{") else v) for c, v in corpo.items()}
    r = cliente.request(metodo, caminho.format(**valores), json=corpo)
    assert r.status_code == 400 and mensagem in r.json()["detail"], r.json()
