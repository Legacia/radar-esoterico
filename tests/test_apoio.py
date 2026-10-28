"""Itens de apoio: a embalagem de cada produto e de cada kit entra nas contas de margem."""
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
import pytest

from radar.api import criar_app
from radar.apoio import excluir_item, indicar, itens_de, retirar, salvar_item
from radar.compras import avaliar_lote, salvar_plano
from radar.fornecedores import excluir_fornecedor, salvar_fornecedor
from radar.kits import margem_kit
from radar.margem import Parametros
from radar.margem.configuracao import obter_configuracao
from radar.mercado import pesquisar, registrar_anuncio
from radar.painel import obter_painel
from radar.produtos import estimar_margem, listar_skus, registrar_cotacao, salvar_produto

EMAIL, SENHA = "teste@example.invalid", "senha-ficticia-123"
HOJE = date.today()


@pytest.fixture
def base(db):
    f = salvar_fornecedor("Fornecedor fictício", "", "", Decimal(0), "", "", caminho=db)
    kit = salvar_produto("Kit fictício 3 incensos + suporte", "", "Candidato", caminho=db)
    sku = registrar_cotacao(f, kit, "KIT-1", Decimal("20.00"), 1, HOJE, Decimal("59.90"), db)
    caixa = salvar_item("Caixa fictícia P", f, Decimal("1.80"), HOJE, caminho=db)
    sacola = salvar_item("Sacola fictícia", None, Decimal("1.35"), HOJE, caminho=db)
    return {"f": f, "produto": kit, "sku": sku, "caixa": caixa, "sacola": sacola}


@pytest.fixture
def cliente(db, conta):
    with TestClient(criar_app()) as c:
        c.post("/api/entrar", json={"email": EMAIL, "senha": SENHA})
        yield c


def _margem(db):
    sku = listar_skus(caminho=db)[0]
    return estimar_margem(sku, obter_configuracao(db).parametros)


def test_sem_itens_vale_a_embalagem_padrao_e_o_caso_obrigatorio(db, base):
    resultado = _margem(db)
    assert resultado.contribuicao == Decimal("14.33")
    assert resultado.margem_pct.quantize(Decimal("0.001")) == Decimal("0.239")


def test_itens_do_produto_substituem_a_embalagem_padrao(db, base):
    indicar("produto", base["produto"], base["caixa"], 1, db)
    indicar("produto", base["produto"], base["sacola"], 2, db)
    # 1,80 + 2 x 1,35 = 4,50 de embalagem, em vez de 2,50: contribuição cai R$ 2,00.
    assert itens_de("produto", base["produto"], db)["embalagem_centavos"] == 450
    assert _margem(db).contribuicao == Decimal("12.33")
    retirar("produto", base["produto"], base["sacola"], db)
    assert _margem(db).contribuicao == Decimal("15.03")  # só a caixa: 1,80
    retirar("produto", base["produto"], base["caixa"], db)
    assert _margem(db).contribuicao == Decimal("14.33")  # volta à padrão


def test_item_gratuito_conta_como_embalagem_zero(db, base):
    brinde = salvar_item("Etiqueta fictícia", None, Decimal("0"), HOJE, caminho=db)
    indicar("produto", base["produto"], brinde, 1, db)
    assert _margem(db).contribuicao == Decimal("16.83")


def test_custo_do_item_atualizado_muda_a_margem(db, base):
    indicar("produto", base["produto"], base["caixa"], 1, db)
    salvar_item("Caixa fictícia P", base["f"], Decimal("2.80"), HOJE, item_id=base["caixa"], caminho=db)
    assert _margem(db).contribuicao == Decimal("14.03")


def test_ficha_do_produto_e_preco_minimo_usam_a_embalagem_propria(cliente, base):
    sku = cliente.get(f"/api/produtos/{base['produto']}").json()["skus"][0]
    assert sku["preco_minimo"] == "55.56" and sku["embalagem"] == "2.50" and not sku["embalagem_propria"]
    cliente.put(f"/api/produtos/{base['produto']}/apoio/{base['caixa']}", json={"quantidade": 1})
    cliente.put(f"/api/produtos/{base['produto']}/apoio/{base['sacola']}", json={"quantidade": 2})
    ficha = cliente.get(f"/api/produtos/{base['produto']}").json()
    sku = ficha["skus"][0]
    # (20 + 4,50 + 4,50 + 3) / (1 - 0,20 - 0,06 - 0,20) = 59,26 (arredondado para cima)
    assert sku["preco_minimo"] == "59.26" and sku["contribuicao"] == "12.33"
    assert sku["embalagem"] == "4.50" and sku["embalagem_propria"]
    assert ficha["apoio"]["embalagem_centavos"] == 450
    assert [(i["nome"], i["quantidade"], i["subtotal_centavos"]) for i in ficha["apoio"]["itens"]] == [
        ("Caixa fictícia P", 1, 180), ("Sacola fictícia", 2, 270)]
    # A ficha do fornecedor mostra a mesma conta.
    assert cliente.get(f"/api/fornecedores/{base['f']}").json()["skus"][0]["contribuicao"] == "12.33"


def test_painel_e_promocao_veem_a_margem_com_a_embalagem_do_produto(db, base):
    assert not [p for p in obter_painel(db)["pendencias"] if p["tipo"] == "Margem abaixo do alvo"]
    cara = salvar_item("Caixa fictícia de madeira", None, Decimal("5.00"), HOJE, caminho=db)
    indicar("produto", base["produto"], cara, 1, db)
    # 14,33 - 2,50 = 11,83 / 59,90 = 19,7%: abaixo do piso de 20%.
    assert [p for p in obter_painel(db)["pendencias"] if p["tipo"] == "Margem abaixo do alvo"]


def test_criterio_de_margem_da_compra_usa_a_embalagem_do_produto(db, base):
    salvar_plano(base["produto"], base["sku"], 1, Decimal("59.90"), caminho=db)
    assert avaliar_lote(db)["itens"][0]["criterios"]["Margem"]
    cara = salvar_item("Caixa fictícia de madeira", None, Decimal("5.00"), HOJE, caminho=db)
    indicar("produto", base["produto"], cara, 1, db)
    item = avaliar_lote(db)["itens"][0]
    assert not item["criterios"]["Margem"] and item["contribuicao"] == Decimal("11.83")


def test_pesquisa_usa_a_embalagem_do_produto(db, base):
    registrar_anuncio("shopee", "Anúncio fictício", "https://example.invalid/a", Decimal("59.90"), HOJE,
                      base["produto"], caminho=db)
    indicar("produto", base["produto"], base["caixa"], 1, db)
    r = pesquisar(base["produto"], base["sku"], caminho=db)
    assert r["linhas"][0]["contribuicao"] == Decimal("15.03") and r["embalagem"] == Decimal("1.8")


def test_kit_usa_a_propria_embalagem_e_ignora_a_dos_componentes(cliente, db, base):
    componente = salvar_produto("Incenso fictício", "", "Candidato", caminho=db)
    cot = registrar_cotacao(base["f"], componente, "INC", Decimal("5.00"), 1, HOJE, None, db)
    cliente.put(f"/api/produtos/{componente}/apoio/{base['sacola']}", json={"quantidade": 3})
    k = cliente.post("/api/kits", json={"nome": "Kit fictício"}).json()["id"]
    cliente.put(f"/api/kits/{k}/componentes/{componente}", json={"quantidade": 4, "cotacao_id": cot})
    assert cliente.put(f"/api/kits/{k}", json={"nome": "Kit fictício", "quantidade_planejada": 0,
                                                "preco_venda": "59,90"}).status_code == 200
    margem = cliente.get(f"/api/kits/{k}").json()["margem"]
    # Custo 4 x 5,00 = 20,00 e embalagem padrão: o caso obrigatório, sem a sacola do componente.
    assert margem["embalagem"] == "2.50" and not margem["embalagem_propria"]
    assert margem["contribuicao"] == "14.33" and margem["preco_minimo"] == "55.56"
    cliente.put(f"/api/kits/{k}/apoio/{base['caixa']}", json={"quantidade": 2})
    ficha = cliente.get(f"/api/kits/{k}").json()
    assert ficha["margem"]["embalagem"] == "3.60" and ficha["margem"]["embalagem_propria"]
    assert ficha["margem"]["contribuicao"] == "13.23" and ficha["preco_venda_centavos"] == 5990
    assert [i["nome"] for i in ficha["apoio"]["itens"]] == ["Caixa fictícia P"]
    # Salvar o plano sem mandar o preço não apaga o preço.
    cliente.put(f"/api/kits/{k}", json={"nome": "Kit fictício", "quantidade_planejada": 2})
    assert cliente.get(f"/api/kits/{k}").json()["preco_venda_centavos"] == 5990
    cliente.put(f"/api/kits/{k}", json={"nome": "Kit fictício", "quantidade_planejada": 2, "preco_venda": ""})
    ficha = cliente.get(f"/api/kits/{k}").json()
    assert ficha["preco_venda_centavos"] is None and ficha["margem"]["contribuicao"] is None
    assert ficha["margem"]["preco_minimo"] == "57.60"  # (20 + 4,50 + 3,60 + 3) / 0,54 = 57,59...


def test_kit_preco_zero_e_recusado_sem_gravar_metade(cliente, base):
    k = cliente.post("/api/kits", json={"nome": "Kit fictício"}).json()["id"]
    r = cliente.put(f"/api/kits/{k}", json={"nome": "Kit fictício", "quantidade_planejada": 5, "preco_venda": "0"})
    assert r.status_code == 400 and "maior que zero" in r.json()["detail"]
    assert cliente.get(f"/api/kits/{k}").json()["quantidade_planejada"] == 0


def test_kit_sem_custo_completo_nao_tem_margem():
    p = Parametros(Decimal("0.2"), Decimal("0.06"), Decimal("0.2"), Decimal("4.50"), Decimal("2.50"), Decimal("3.00"))
    r = margem_kit(None, 5990, None, p)
    assert r["contribuicao"] is None and r["preco_minimo"] is None and r["embalagem"] == Decimal("2.50")


def test_validacoes_do_item(db, base):
    with pytest.raises(ValueError, match="nome do item"):
        salvar_item("  ", None, Decimal("1"), HOJE, caminho=db)
    with pytest.raises(ValueError, match="data futura"):
        salvar_item("Fita fictícia", None, Decimal("1"), HOJE + timedelta(days=1), caminho=db)
    with pytest.raises(ValueError, match="duas casas"):
        salvar_item("Fita fictícia", None, Decimal("1.001"), HOJE, caminho=db)
    with pytest.raises(ValueError, match="Fornecedor não encontrado"):
        salvar_item("Fita fictícia", 999, Decimal("1"), HOJE, caminho=db)
    for quantidade in (0, 1001, True, "2"):
        with pytest.raises(ValueError, match="1 a 1000"):
            indicar("produto", base["produto"], base["caixa"], quantidade, db)
    with pytest.raises(ValueError, match="Produto não encontrado"):
        indicar("produto", 999, base["caixa"], 1, db)
    with pytest.raises(ValueError, match="Kit não encontrado"):
        indicar("kit", 999, base["caixa"], 1, db)
    with pytest.raises(ValueError, match="Item de apoio não encontrado"):
        indicar("produto", base["produto"], 999, 1, db)


def test_exclusao_so_sem_uso_e_conferindo_o_nome(db, base):
    indicar("produto", base["produto"], base["caixa"], 1, db)
    with pytest.raises(ValueError, match="indicado em produtos"):
        excluir_item(base["caixa"], "Caixa fictícia P", db)
    with pytest.raises(ValueError, match="recarregue"):
        excluir_item(base["sacola"], "Outro nome", db)
    excluir_item(base["sacola"], "Sacola fictícia", db)
    with pytest.raises(ValueError, match="recarregue"):
        excluir_item(base["sacola"], "Sacola fictícia", db)


def test_fornecedor_com_item_de_apoio_nao_e_excluido(db):
    f = salvar_fornecedor("Fornecedor de caixas fictício", "", "", Decimal(0), "", "", caminho=db)
    salvar_item("Caixa fictícia", f, Decimal("1"), HOJE, caminho=db)
    with pytest.raises(ValueError, match=r"item\(ns\) de apoio"):
        excluir_fornecedor(f, "Fornecedor de caixas fictício", db)


def test_rotas_da_tela_de_itens(cliente, base):
    lista = cliente.get("/api/apoio").json()
    assert [i["nome"] for i in lista["itens"]] == ["Caixa fictícia P", "Sacola fictícia"]
    assert lista["itens"][0]["fornecedor"] == "Fornecedor fictício"
    novo = cliente.post("/api/apoio", json={"nome": "Papel de seda fictício", "custo": "0,25",
                                            "data": HOJE.isoformat()}).json()["id"]
    assert cliente.put(f"/api/apoio/{novo}", json={"nome": "Papel de seda fictício", "custo": "0,30",
                                                    "data": HOJE.isoformat(), "fornecedor_id": base["f"]}).status_code == 200
    item = [i for i in cliente.get("/api/apoio").json()["itens"] if i["id"] == novo][0]
    assert item["custo_centavos"] == 30 and item["fornecedor_id"] == base["f"]
    assert cliente.post("/api/apoio", json={"nome": "X", "custo": "abc", "data": HOJE.isoformat()}).status_code == 400
    assert cliente.delete(f"/api/apoio/{novo}", params={"nome": "Papel de seda fictício"}).status_code == 200


def test_rotas_exigem_sessao(db, base):
    with TestClient(criar_app()) as anonimo:
        for metodo, rota in (("get", "/api/apoio"), ("post", "/api/apoio"), ("put", f"/api/apoio/{base['caixa']}"),
                             ("delete", f"/api/apoio/{base['caixa']}?nome=x"),
                             ("put", f"/api/produtos/{base['produto']}/apoio/{base['caixa']}"),
                             ("delete", f"/api/produtos/{base['produto']}/apoio/{base['caixa']}"),
                             ("put", f"/api/kits/1/apoio/{base['caixa']}"), ("delete", f"/api/kits/1/apoio/{base['caixa']}")):
            assert getattr(anonimo, metodo)(rota).status_code == 401
