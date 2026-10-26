"""SQLite local: conexões curtas, integridade e migrações transacionais."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3

CAMINHO_PADRAO = Path(__file__).resolve().parents[2] / "data" / "radar.db"


@contextmanager
def conectar(caminho=None):
    destino = Path(caminho) if caminho is not None else CAMINHO_PADRAO
    destino.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(destino, timeout=5)
    conexao.row_factory = sqlite3.Row
    try:
        conexao.execute("PRAGMA foreign_keys = ON")
        conexao.execute("PRAGMA busy_timeout = 5000")
        conexao.execute("PRAGMA journal_mode = WAL")
        yield conexao
        conexao.commit()
    except BaseException:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def inicializar(caminho=None):
    from radar.banco.esquema import MIGRACOES

    with conectar(caminho) as conexao:
        conexao.execute("BEGIN IMMEDIATE")
        versao = conexao.execute("PRAGMA user_version").fetchone()[0]
        if versao > len(MIGRACOES):
            raise RuntimeError("Banco de uma versão mais nova do Radar. Atualize o programa.")
        for numero in range(versao, len(MIGRACOES)):
            for comando in MIGRACOES[numero]:
                conexao.execute(comando)
            conexao.execute(f"PRAGMA user_version = {numero + 1}")
