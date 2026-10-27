from decimal import Decimal as D

from radar.banco import conectar, inicializar
from radar.banco.esquema import MIGRACOES
from radar.compras import obter_orcamento
from radar.usuarios import autenticar, criar_usuario


def test_migra_v2_preservando_dados_sem_classificar_contatos_antigos(tmp_path):
    db = tmp_path / "versao2.db"
    with conectar(db) as c:
        for migracao in MIGRACOES[:2]:
            for comando in migracao:
                c.execute(comando)
        c.execute("PRAGMA user_version=2")
        c.execute("INSERT INTO fornecedor(id,nome) VALUES(1,'Fictício')")
        c.execute("INSERT INTO produto(id,nome) VALUES(1,'Fictício')")
        c.execute("INSERT INTO interacao(fornecedor_id,data,canal,resumo) VALUES(1,'2026-10-01','Telefone','Fictício')")
        c.execute("INSERT INTO kit(id,nome) VALUES(1,'Fictício')")
        c.execute("INSERT INTO kit_item(kit_id,produto_id,quantidade) VALUES(1,1,3)")
    criar_usuario("Fictício","migracao3@example.invalid","senha-ficticia-123",db)
    inicializar(db)
    inicializar(db)
    assert autenticar("migracao3@example.invalid","senha-ficticia-123",db)
    assert obter_orcamento(db)["total_centavos"] == 100000
    with conectar(db) as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == 3
        assert c.execute("SELECT situacao_resposta FROM interacao").fetchone()[0] is None
        assert c.execute("SELECT sku_fornecedor_id FROM kit_item").fetchone()[0] is None
        assert c.execute("SELECT quantidade FROM kit_item").fetchone()[0] == 3
        assert c.execute("SELECT estoque_atual FROM produto").fetchone()[0] == 0
        assert c.execute("SELECT validado FROM produto").fetchone()[0] == 0
