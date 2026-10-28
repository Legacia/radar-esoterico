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
    excluir_fornecedor(vazio, "Sem histórico", db)
    assert [f["nome"] for f in listar_fornecedores(db)] == ["Fornecedor fictício"]


def test_fornecedor_com_cotacao_ou_contato_nao_e_excluido(db, base):
    registrar_cotacao(base["f"], base["p"], "INC", Decimal("4.50"), 1, HOJE, None, db)
    registrar_interacao(base["f"], HOJE, "WhatsApp", "Pedido de cotação", db)
    with pytest.raises(ValueError, match=r"1 cotação\(ões\) e 1 contato\(s\).*Descartado ou pausado"):
        excluir_fornecedor(base["f"], "Fornecedor fictício", db)
    assert len(listar_fornecedores(db)) == 1


def test_fornecedor_inexistente(db):
    with pytest.raises(ValueError, match="Fornecedor não encontrado."):
        excluir_fornecedor(99, "Qualquer", db)


def test_excluir_sku_apaga_todas_as_cotacoes_do_codigo_sem_diferenciar_maiusculas(db, base):
    antiga = registrar_cotacao(base["f"], base["p"], "inc", Decimal("4.00"), 1, HOJE - timedelta(days=30), None, db)
    atual = registrar_cotacao(base["f"], base["p"], "INC", Decimal("4.50"), 1, HOJE, None, db)
    outro = registrar_cotacao(base["f"], base["p"], "INC-2", Decimal("5.00"), 1, HOJE, None, db)
    assert excluir_sku(atual, base["f"], "INC", db) == 2
    assert [s["id"] for s in listar_skus(caminho=db)] == [outro]
    with conectar(db) as c:
        assert c.execute("SELECT 1 FROM sku_fornecedor WHERE id=?", (antiga,)).fetchone() is None
    # Sem cotações, o fornecedor passa a poder ser excluído.
    excluir_sku(outro, base["f"], "INC-2", db)
    excluir_fornecedor(base["f"], "Fornecedor fictício", db)


def test_sku_em_kit_ou_plano_de_compra_nao_e_excluido(db, base):
    antiga = registrar_cotacao(base["f"], base["p"], "INC", Decimal("4.00"), 1, HOJE - timedelta(days=30), None, db)
    atual = registrar_cotacao(base["f"], base["p"], "INC", Decimal("4.50"), 1, HOJE, None, db)
    # O kit usa a cotação antiga: o código inteiro fica protegido, mesmo excluindo pela atual.
    salvar_componente(salvar_kit("Kit fictício", caminho=db), base["p"], 3, antiga, db)
    with pytest.raises(ValueError, match="em uso em kits"):
        excluir_sku(atual, base["f"], "INC", db)
    p2 = salvar_produto("Suporte fictício", "", "Candidato", caminho=db)
    sup = registrar_cotacao(base["f"], p2, "SUP", Decimal("6.00"), 1, HOJE, None, db)
    salvar_plano(p2, sup, 2, Decimal("30.00"), caminho=db)
    with pytest.raises(ValueError, match="em uso em plano de compra"):
        excluir_sku(sup, base["f"], "SUP", db)
    assert len(listar_skus(caminho=db)) == 2


def test_rotas_de_exclusao(db, conta, base):
    vazio = salvar_fornecedor("Sem histórico", "", "", Decimal(0), "", "", caminho=db)
    sku = registrar_cotacao(base["f"], base["p"], "INC", Decimal("4.50"), 1, HOJE, None, db)
    with TestClient(criar_app()) as cliente:
        assert cliente.delete(f"/api/fornecedores/{vazio}", params={"nome": "Sem histórico"}).status_code == 401
        cliente.post("/api/entrar", json={"email": EMAIL, "senha": SENHA})
        assert cliente.delete(f"/api/fornecedores/{vazio}", params={"nome": "Sem histórico"}).json() == {"ok": True}
        bloqueado = cliente.delete(f"/api/fornecedores/{base['f']}", params={"nome": "Fornecedor fictício"})
        assert bloqueado.status_code == 400 and "Não é possível excluir" in bloqueado.json()["detail"]
        assert cliente.delete(f"/api/cotacoes/{sku}", params={"fornecedor_id": base["f"], "codigo": "inc"}).json() == {"apagadas": 1}
        assert cliente.delete(f"/api/cotacoes/{sku}", params={"fornecedor_id": base["f"], "codigo": "inc"}).json()["detail"].startswith("Cotação não encontrada.")
        assert cliente.delete(f"/api/fornecedores/{base['f']}", params={"nome": "Fornecedor fictício"}).json() == {"ok": True}


def test_id_reaproveitado_nao_apaga_outro_registro(db, base):
    # Alfa é excluído e Beta recebe o mesmo id; a confirmação antiga (nome Alfa) não apaga Beta.
    alfa = salvar_fornecedor("Alfa fictício", "", "", Decimal(0), "", "", caminho=db)
    excluir_fornecedor(alfa, "Alfa fictício", db)
    beta = salvar_fornecedor("Beta fictício", "", "", Decimal(0), "", "", caminho=db)
    assert beta == alfa
    with pytest.raises(ValueError, match="Recarregue a ficha"):
        excluir_fornecedor(alfa, "Alfa fictício", db)
    assert "Beta fictício" in [f["nome"] for f in listar_fornecedores(db)]
    # O mesmo vale para SKU: id reaproveitado por outro código não é apagado.
    velho = registrar_cotacao(base["f"], base["p"], "VELHO", Decimal("1.00"), 1, HOJE, None, db)
    excluir_sku(velho, base["f"], "VELHO", db)
    novo = registrar_cotacao(base["f"], base["p"], "NOVO", Decimal("1.00"), 1, HOJE, None, db)
    assert novo == velho
    with pytest.raises(ValueError, match="recarregue a tela"):
        excluir_sku(velho, base["f"], "VELHO", db)
    with pytest.raises(ValueError, match="recarregue a tela"):
        excluir_sku(novo, beta, "NOVO", db)
    assert [s["codigo"] for s in listar_skus(caminho=db)] == ["NOVO"]


def test_excluir_sku_recalcula_a_data_da_ultima_cotacao(db, base):
    registrar_cotacao(base["f"], base["p"], "ANTIGO", Decimal("1.00"), 1, date(2026, 9, 28), None, db)
    recente = registrar_cotacao(base["f"], base["p"], "RECENTE", Decimal("1.00"), 1, date(2026, 10, 28), None, db)
    excluir_sku(recente, base["f"], "RECENTE", db)
    with conectar(db) as c:
        assert c.execute("SELECT data_ultima_cotacao FROM fornecedor WHERE id=?", (base["f"],)).fetchone()[0] == "2026-09-28"
    excluir_sku(listar_skus(caminho=db)[0]["id"], base["f"], "antigo", db)
    with conectar(db) as c:
        assert c.execute("SELECT data_ultima_cotacao FROM fornecedor WHERE id=?", (base["f"],)).fetchone()[0] is None
