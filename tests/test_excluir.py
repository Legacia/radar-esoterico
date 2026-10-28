from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
import pytest

from radar.api import criar_app
from radar.banco import conectar
from radar.compras import salvar_plano
from radar.fornecedores import excluir_fornecedor, listar_fornecedores, registrar_interacao, salvar_fornecedor
from radar.kits import salvar_componente, salvar_kit
from radar.produtos import excluir_sku, listar_skus, registrar_cotacao, salvar_produto

EMAIL, SENHA = "teste@example.invalid", "senha-ficticia-123"
HOJE = date.today()


@pytest.fixture
def base(db):
    f = salvar_fornecedor("Fornecedor fictício", "", "", Decimal(0), "", "", caminho=db)
    p = salvar_produto("Incenso fictício", "", "Candidato", caminho=db)
    return {"f": f, "p": p}


def test_fornecedor_sem_historico_e_excluido(db, base):
    vazio = salvar_fornecedor("Sem histórico", "", "", Decimal(0), "", "", caminho=db)
    excluir_fornecedor(vazio, db)
    assert [f["nome"] for f in listar_fornecedores(db)] == ["Fornecedor fictício"]


def test_fornecedor_com_cotacao_ou_contato_nao_e_excluido(db, base):
    registrar_cotacao(base["f"], base["p"], "INC", Decimal("4.50"), 1, HOJE, None, db)
    registrar_interacao(base["f"], HOJE, "WhatsApp", "Pedido de cotação", db)
    with pytest.raises(ValueError, match=r"1 cotação\(ões\) e 1 contato\(s\).*Descartado ou pausado"):
        excluir_fornecedor(base["f"], db)
    assert len(listar_fornecedores(db)) == 1


def test_fornecedor_inexistente(db):
    with pytest.raises(ValueError, match="Fornecedor não encontrado."):
        excluir_fornecedor(99, db)


def test_excluir_sku_apaga_todas_as_cotacoes_do_codigo_sem_diferenciar_maiusculas(db, base):
    antiga = registrar_cotacao(base["f"], base["p"], "inc", Decimal("4.00"), 1, HOJE - timedelta(days=30), None, db)
    atual = registrar_cotacao(base["f"], base["p"], "INC", Decimal("4.50"), 1, HOJE, None, db)
    outro = registrar_cotacao(base["f"], base["p"], "INC-2", Decimal("5.00"), 1, HOJE, None, db)
    assert excluir_sku(atual, db) == 2
    assert [s["id"] for s in listar_skus(caminho=db)] == [outro]
    with conectar(db) as c:
        assert c.execute("SELECT 1 FROM sku_fornecedor WHERE id=?", (antiga,)).fetchone() is None
    # Sem cotações, o fornecedor passa a poder ser excluído.
    excluir_sku(outro, db)
    excluir_fornecedor(base["f"], db)


def test_sku_em_kit_ou_plano_de_compra_nao_e_excluido(db, base):
    antiga = registrar_cotacao(base["f"], base["p"], "INC", Decimal("4.00"), 1, HOJE - timedelta(days=30), None, db)
    atual = registrar_cotacao(base["f"], base["p"], "INC", Decimal("4.50"), 1, HOJE, None, db)
    # O kit usa a cotação antiga: o código inteiro fica protegido, mesmo excluindo pela atual.
    salvar_componente(salvar_kit("Kit fictício", caminho=db), base["p"], 3, antiga, db)
    with pytest.raises(ValueError, match="em uso em kits"):
        excluir_sku(atual, db)
    p2 = salvar_produto("Suporte fictício", "", "Candidato", caminho=db)
    sup = registrar_cotacao(base["f"], p2, "SUP", Decimal("6.00"), 1, HOJE, None, db)
    salvar_plano(p2, sup, 2, Decimal("30.00"), caminho=db)
    with pytest.raises(ValueError, match="em uso em plano de compra"):
        excluir_sku(sup, db)
    assert len(listar_skus(caminho=db)) == 2


def test_rotas_de_exclusao(db, conta, base):
    vazio = salvar_fornecedor("Sem histórico", "", "", Decimal(0), "", "", caminho=db)
    sku = registrar_cotacao(base["f"], base["p"], "INC", Decimal("4.50"), 1, HOJE, None, db)
    with TestClient(criar_app()) as cliente:
        assert cliente.delete(f"/api/fornecedores/{vazio}").status_code == 401
        cliente.post("/api/entrar", json={"email": EMAIL, "senha": SENHA})
        assert cliente.delete(f"/api/fornecedores/{vazio}").json() == {"ok": True}
        bloqueado = cliente.delete(f"/api/fornecedores/{base['f']}")
        assert bloqueado.status_code == 400 and "Não é possível excluir" in bloqueado.json()["detail"]
        assert cliente.delete(f"/api/cotacoes/{sku}").json() == {"apagadas": 1}
        assert cliente.delete(f"/api/cotacoes/{sku}").json()["detail"] == "Cotação não encontrada."
        assert cliente.delete(f"/api/fornecedores/{base['f']}").json() == {"ok": True}
