from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
import pytest

from radar.api import criar_app
from radar.fornecedores import salvar_fornecedor
from radar.produtos import registrar_cotacao, salvar_produto

EMAIL, SENHA = "teste@example.invalid", "senha-ficticia-123"
HOJE = date.today().isoformat()


@pytest.fixture
def cliente(db, conta):
    with TestClient(criar_app()) as c:
        c.post("/api/entrar", json={"email": EMAIL, "senha": SENHA})
        yield c


@pytest.fixture
def base(db):
    f = salvar_fornecedor("Fornecedor fictício", "", "", Decimal(0), "", "", caminho=db)
    p = salvar_produto("Kit fictício", "", "Candidato", caminho=db)
    outro = salvar_produto("Outro produto fictício", "", "Candidato", caminho=db)
    cot = registrar_cotacao(f, p, "KIT-01", Decimal("20.00"), 10, date.today(), None, db)
    return {"produto": p, "outro": outro, "cotacao": cot, "fornecedor": f, "db": db}


def anunciar(cliente, **campos):
    dados = {"marketplace": "Marketplace Fictício", "titulo": "Kit fictício 3 incensos",
             "url": "https://example.invalid/kit-1", "preco": "59,90", "data": HOJE, **campos}
    return cliente.post("/api/pesquisa/anuncios", json=dados)


def test_cadastra_anuncio_e_lista_com_produtos(cliente, base):
    r = anunciar(cliente, produto_id=base["produto"])
    assert r.status_code == 200 and r.json()["novo_preco"] is True
    lista = cliente.get("/api/pesquisa/anuncios").json()
    assert lista["anuncios"][0]["produto"] == "Kit fictício"
    assert lista["anuncios"][0]["marketplace"] == "marketplace fictício"
    assert {p["nome"] for p in lista["produtos"]} == {"Kit fictício", "Outro produto fictício"}


def test_mesmo_preco_na_mesma_data_nao_duplica(cliente, base):
    anunciar(cliente, produto_id=base["produto"])
    r = anunciar(cliente, produto_id=base["produto"])
    assert r.json()["novo_preco"] is False


def test_pesquisa_traz_caso_da_margem_e_simulacao_livre(cliente, base):
    anunciar(cliente, produto_id=base["produto"])
    anunciar(cliente, produto_id=base["produto"], url="https://example.invalid/kit-2", preco="40,00",
             sinal="Mais vendido na categoria")
    r = cliente.get("/api/pesquisa", params={"produto_id": base["produto"], "cotacao_id": base["cotacao"]}).json()
    assert [l["preco_centavos"] for l in r["linhas"]] == [4000, 5990]
    caso = r["linhas"][1]
    assert Decimal(caso["contribuicao"]) == Decimal("14.33")
    assert round(Decimal(caso["margem_pct"]), 3) == Decimal("0.239")
    assert r["preco_minimo"] == "55.56"
    assert Decimal(r["mediana"]) == Decimal("49.95")
    assert r["no_alvo"] == 1 and r["custo_centavos"] == 2000
    assert r["cotacao_antiga"] is False and r["marketplaces"] == ["marketplace fictício"]
    assert r["linhas"][0]["sinal"] == "Mais vendido na categoria"
    assert len(r["historico"]) == 2


def test_alvo_abaixo_de_20_vale_na_pesquisa(cliente, base):
    anunciar(cliente, produto_id=base["produto"], preco="50,00")
    padrao = {"comissao": "20", "tributo": "6", "tarifa_fixa": "4,50", "embalagem": "2,50", "outros": "3,00",
              "limite_cotacao_dias": 15}
    params = {"produto_id": base["produto"], "cotacao_id": base["cotacao"]}
    assert cliente.get("/api/pesquisa", params=params).json()["no_alvo"] == 0
    cliente.put("/api/configuracao", json={**padrao, "margem_alvo": "10"})
    r = cliente.get("/api/pesquisa", params=params).json()
    assert r["no_alvo"] == 1 and Decimal(r["margem_alvo_pct"]) == Decimal("0.10")


def test_filtros_e_cotacao_antiga(cliente, base):
    db = base["db"]
    antiga = registrar_cotacao(base["fornecedor"], base["produto"], "KIT-02", Decimal("18.00"), 1,
                               date.today() - timedelta(days=40), None, db)
    anunciar(cliente, produto_id=base["produto"])
    anunciar(cliente, produto_id=base["produto"], marketplace="Outra loja", url="https://example.invalid/x", titulo="Suporte")
    params = {"produto_id": base["produto"], "cotacao_id": antiga}
    assert cliente.get("/api/pesquisa", params=params).json()["cotacao_antiga"] is True
    so_um = cliente.get("/api/pesquisa", params={**params, "marketplace": "OUTRA LOJA"}).json()
    assert [l["titulo"] for l in so_um["linhas"]] == ["Suporte"]
    busca = cliente.get("/api/pesquisa", params={**params, "termo": "INCENSOS"}).json()
    assert [l["titulo"] for l in busca["linhas"]] == ["Kit fictício 3 incensos"]
    cotacoes = cliente.get("/api/pesquisa/cotacoes", params={"produto_id": base["produto"]}).json()
    assert [c["codigo"] for c in cotacoes] == ["KIT-01", "KIT-02"]


def test_vincular_e_desvincular(cliente, base):
    anuncio = anunciar(cliente).json()["anuncio_id"]
    assert cliente.put(f"/api/pesquisa/anuncios/{anuncio}/produto", json={"produto_id": base["outro"]}).status_code == 200
    assert cliente.get("/api/pesquisa/anuncios").json()["anuncios"][0]["produto"] == "Outro produto fictício"
    assert cliente.put(f"/api/pesquisa/anuncios/{anuncio}/produto", json={"produto_id": None}).status_code == 200
    assert cliente.get("/api/pesquisa/anuncios").json()["anuncios"][0]["produto_id"] is None
    r = cliente.put("/api/pesquisa/anuncios/999/produto", json={"produto_id": None})
    assert r.status_code == 400 and r.json()["detail"] == "Anúncio não encontrado."


@pytest.mark.parametrize("campos, mensagem", [
    ({"url": "ftp://example.invalid/x"}, "http ou https"),
    ({"url": "https://usuario:senha@example.invalid/x"}, "sem credenciais"),
    ({"preco": "0"}, "maior que zero"),
    ({"preco": "1,999"}, "duas casas"),
    ({"data": (date.today() + timedelta(days=1)).isoformat()}, "data futura"),
    ({"titulo": " "}, "Informe o título"),
    ({"produto_id": 999}, "Produto não encontrado"),
])
def test_anuncio_invalido_explica(cliente, base, campos, mensagem):
    r = anunciar(cliente, **campos)
    assert r.status_code == 400 and mensagem in r.json()["detail"]


def test_cotacao_de_outro_produto_e_recusada(cliente, base):
    r = cliente.get("/api/pesquisa", params={"produto_id": base["outro"], "cotacao_id": base["cotacao"]})
    assert r.status_code == 400 and "cotação do produto pesquisado" in r.json()["detail"]
