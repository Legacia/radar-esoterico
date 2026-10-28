from decimal import Decimal as D

from radar.banco import conectar, inicializar
from radar.banco.esquema import MIGRACOES
from radar.margem.configuracao import obter_configuracao
from radar.produtos import listar_skus
from radar.usuarios import autenticar, criar_usuario


def test_atualiza_banco_v1_preservando_usuario_cotacoes_e_tarefas(tmp_path):
    db = tmp_path / "versao1.db"
    with conectar(db) as c:
        for comando in MIGRACOES[0]:
            c.execute(comando)
        c.execute("PRAGMA user_version=1")
        c.execute("INSERT INTO fornecedor(id,nome) VALUES (1,'Fictício')")
        c.execute("INSERT INTO produto(id,nome) VALUES (1,'Fictício')")
        c.execute("""INSERT INTO sku_fornecedor(fornecedor_id,produto_id,codigo,custo_unitario_centavos,
            quantidade_minima,data_cotacao) VALUES(1,1,'ANTIGO',2000,1,'2026-10-26')""")
        c.execute("INSERT INTO tarefa(titulo,semana,responsavel) VALUES('Fictícia',1,'Fictício')")
    criar_usuario("Fictício", "migracao@example.invalid", "senha-ficticia-123", db)
    inicializar(db)
    inicializar(db)
    assert autenticar("migracao@example.invalid", "senha-ficticia-123", db)
    assert listar_skus(caminho=db)[0]["preco_venda_centavos"] is None
    assert obter_configuracao(db).parametros.tarifa_fixa == D("4.50")
    with conectar(db) as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == 4
        assert c.execute("SELECT count(*) FROM tarefa").fetchone()[0] == 1
