from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
import pytest

from radar.api import criar_app
from radar.fornecedores import salvar_fornecedor

EMAIL, SENHA = "teste@example.invalid", "senha-ficticia-123"
HOJE = date.today().isoformat()


@pytest.fixture
def cliente(db, conta):
    with TestClient(criar_app()) as c:
        c.post("/api/entrar", json={"email": EMAIL, "senha": SENHA})
        yield c


@pytest.fixture
def fornecedor(db):
    return salvar_fornecedor("Fornecedor fictício", "", "", Decimal(0), "", "", caminho=db)


def novo(cliente, **campos):
    resposta = cliente.post("/api/produtos", json={"nome": "Kit fictício", **campos})
    assert resposta.status_code == 200, resposta.json()
    return resposta.json()["id"]


def cotar(cliente, produto, fornecedor, **campos):
    dados = {"fornecedor_id": fornecedor, "codigo": "KIT-01", "custo": "20,00", "quantidade_minima": 10,
             "data": HOJE, "preco_venda": "59,90", **campos}
    return cliente.post(f"/api/produtos/{produto}/cotacoes", json=dados)


def test_catalogo_traz_produtos_e_fornecedores(cliente, fornecedor):
    p = novo(cliente, familia="Incensos", qualidade_conferida=True)
    r = cliente.get("/api/produtos").json()
    assert r["fornecedores"] == [{"id": fornecedor, "nome": "Fornecedor fictício"}]
    assert r["produtos"] == [{"id": p, "nome": "Kit fictício", "familia": "Incensos", "status": "Candidato",
        "especificacoes_conferidas": 0, "procedencia_conferida": 0, "qualidade_conferida": 1,
        "validado": 0, "estoque_atual": 0}]


def test_alterar_produto(cliente):
    p = novo(cliente)
    assert cliente.put(f"/api/produtos/{p}", json={"nome": "Kit fictício 2", "status": "Descartado",
                                                    "especificacoes_conferidas": True}).status_code == 200
    ficha = cliente.get(f"/api/produtos/{p}").json()
    assert ficha["nome"] == "Kit fictício 2" and ficha["status"] == "Descartado"
    assert ficha["especificacoes_conferidas"] == 1


def test_cotacao_com_caso_da_margem(cliente, fornecedor):
    p = novo(cliente)
    assert cotar(cliente, p, fornecedor).status_code == 200
    ficha = cliente.get(f"/api/produtos/{p}").json()
    sku = ficha["skus"][0]
    assert sku["fornecedor"] == "Fornecedor fictício" and sku["custo_centavos"] == 2000
    assert sku["preco_venda_centavos"] == 5990
    assert Decimal(sku["contribuicao"]) == Decimal("14.33")
    assert round(Decimal(sku["margem_pct"]), 3) == Decimal("0.239")
    assert sku["preco_minimo"] == "55.56"
    assert ficha["limite_cotacao_dias"] == 15


def test_recotacao_mantem_um_codigo_e_preco_opcional(cliente, fornecedor):
    p = novo(cliente)
    cotar(cliente, p, fornecedor, data=(date.today() - timedelta(days=30)).isoformat())
    assert cotar(cliente, p, fornecedor, codigo="kit-01", custo="22", preco_venda="  ").status_code == 200
    skus = cliente.get(f"/api/produtos/{p}").json()["skus"]
    assert len(skus) == 1
    assert skus[0]["codigo"] == "KIT-01" and skus[0]["custo_centavos"] == 2200
    assert skus[0]["preco_venda_centavos"] is None and skus[0]["margem_pct"] is None
    assert skus[0]["cotacao_antiga"] is False


@pytest.mark.parametrize("campos, mensagem", [
    ({"codigo": " "}, "Informe o código"),
    ({"custo": "abc"}, "Informe um número"),
    ({"custo": "1,999"}, "no máximo duas casas"),
    ({"quantidade_minima": 0}, "quantidade mínima"),
    ({"quantidade_minima": "10"}, "formato inválido"),
    ({"preco_venda": "0"}, "preço conservador deve ser maior que zero"),
    ({"data": (date.today() + timedelta(days=1)).isoformat()}, "data futura"),
    ({"data": "27/10/2026"}, "data válida"),
    ({"fornecedor_id": 999}, "Fornecedor não encontrado"),
])
def test_cotacao_invalida_explica(cliente, fornecedor, campos, mensagem):
    p = novo(cliente)
    resposta = cotar(cliente, p, fornecedor, **campos)
    assert resposta.status_code == 400
    assert mensagem in resposta.json()["detail"]


def test_mesmo_codigo_em_outro_produto_e_recusado(cliente, fornecedor):
    p, q = novo(cliente), novo(cliente, nome="Outro produto fictício")
    cotar(cliente, p, fornecedor)
    resposta = cotar(cliente, q, fornecedor, codigo="kit-01")
    assert resposta.status_code == 400 and "outro produto" in resposta.json()["detail"]


def test_produto_invalido_e_inexistente(cliente, fornecedor):
    assert cliente.post("/api/produtos", json={"nome": " "}).json()["detail"] == "Informe o nome do produto."
    assert cliente.post("/api/produtos", json={"nome": "X", "status": ""}).json()["detail"] == "Informe o status do produto."
    for metodo, caminho, corpo in [("GET", "/api/produtos/999", None), ("PUT", "/api/produtos/999", {"nome": "X"})]:
        resposta = cliente.request(metodo, caminho, json=corpo)
        assert resposta.status_code == 400 and resposta.json()["detail"] == "Produto não encontrado."
    resposta = cotar(cliente, 999, fornecedor)
    assert resposta.status_code == 400 and resposta.json()["detail"] == "Produto não encontrado."
