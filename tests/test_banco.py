import sqlite3

import pytest

from radar.banco import conectar, inicializar


def test_esquema_completo_wal_timeout_e_chaves(db):
    with conectar(db) as c:
        tabelas = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert tabelas == {"usuario", "fornecedor", "interacao", "produto", "sku_fornecedor",
                           "anuncio", "preco_observado", "kit", "kit_item", "cenario_margem", "tarefa", "configuracao", "orcamento", "plano_compra"}
        assert c.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert c.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
        assert c.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert c.execute("PRAGMA user_version").fetchone()[0] == 3


def test_reinicializar_preserva_dados(db):
    with conectar(db) as c:
        c.execute("INSERT INTO tarefa(titulo, semana, responsavel) VALUES ('Teste', 1, 'Fictício')")
    inicializar(db)
    with conectar(db) as c:
        assert c.execute("SELECT count(*) FROM tarefa").fetchone()[0] == 1


def test_migracao_futura_transacional(db, monkeypatch):
    import radar.banco.esquema as esquema
    monkeypatch.setattr(esquema, "MIGRACOES", esquema.MIGRACOES + ((
        "CREATE TABLE teste_migracao (id INTEGER)", "SQL INVALIDO",
    ),))
    with pytest.raises(sqlite3.OperationalError):
        inicializar(db)
    with conectar(db) as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == 3
        assert c.execute("SELECT name FROM sqlite_master WHERE name='teste_migracao'").fetchone() is None


def test_recusa_banco_mais_novo(db):
    with conectar(db) as c:
        c.execute("PRAGMA user_version = 999")
    with pytest.raises(RuntimeError, match="mais nova"):
        inicializar(db)


@pytest.mark.parametrize("semana", [0, 5, 1.5])
def test_semana_invalida(db, semana):
    with pytest.raises(sqlite3.IntegrityError), conectar(db) as c:
        c.execute("INSERT INTO tarefa(titulo, semana, responsavel) VALUES ('Teste', ?, 'Fictício')", (semana,))


def test_sku_recusa_vinculos_inexistentes(db):
    with pytest.raises(sqlite3.IntegrityError), conectar(db) as c:
        c.execute("""INSERT INTO sku_fornecedor(fornecedor_id, produto_id, codigo,
            custo_unitario_centavos, quantidade_minima, data_cotacao)
            VALUES (999, 999, 'FICTICIO', 2000, 1, '2026-10-26')""")


@pytest.mark.parametrize("valor", [-1, 20.5])
def test_dinheiro_recusa_negativo_ou_fracao_de_centavo(db, valor):
    with pytest.raises(sqlite3.IntegrityError), conectar(db) as c:
        c.execute("INSERT INTO fornecedor(nome, pedido_minimo_centavos) VALUES ('Fictício', ?)", (valor,))


def test_erro_reverte_gravacao(db):
    with pytest.raises(ValueError), conectar(db) as c:
        c.execute("INSERT INTO produto(nome) VALUES ('Fictício')")
        raise ValueError("falha simulada")
    with conectar(db) as c:
        assert c.execute("SELECT count(*) FROM produto").fetchone()[0] == 0
