"""Backup do banco: python -m radar.backup [--manter N].

Usa a cópia online do próprio SQLite, que funciona com o Radar aberto (modo WAL) e nunca deixa
uma cópia pela metade. Cada cópia é conferida (integrity_check) antes de ser guardada em backups/,
com a data e a hora no nome. Guarda as N cópias mais recentes (padrão: 30) e apaga só as mais
antigas desta pasta, nunca o banco em uso. A pasta backups/ fica fora do Git.
"""
import argparse
from datetime import datetime
from pathlib import Path
import sqlite3

import radar.banco as banco

PASTA_PADRAO = Path(__file__).resolve().parents[1] / "backups"
MANTER_PADRAO = 30
PREFIXO = "radar-"


def fazer_backup(origem=None, pasta=None, manter=MANTER_PADRAO, agora=None):
    """Copia o banco para a pasta de backups e devolve o caminho da cópia nova."""
    origem = Path(origem) if origem is not None else banco.CAMINHO_PADRAO
    pasta = Path(pasta) if pasta is not None else PASTA_PADRAO
    if type(manter) is not int or manter < 1:
        raise ValueError("Informe quantas cópias guardar: um inteiro maior que zero.")
    if not origem.is_file():
        # Não cria um banco vazio só para copiar: avisa que não há o que guardar.
        raise ValueError(f"Banco não encontrado em {origem}. Nada para copiar.")
    pasta.mkdir(parents=True, exist_ok=True)
    momento = (agora or datetime.now()).strftime("%Y-%m-%d_%H%M%S")
    destino = pasta / f"{PREFIXO}{momento}.db"
    numero = 1
    while destino.exists():
        numero += 1
        destino = pasta / f"{PREFIXO}{momento}-{numero}.db"
    temporario = destino.with_suffix(".parcial")

    fonte = sqlite3.connect(f"file:{origem.as_posix()}?mode=ro", uri=True, timeout=5)
    try:
        copia = sqlite3.connect(temporario)
        try:
            fonte.backup(copia)
            resultado = copia.execute("PRAGMA integrity_check").fetchone()[0]
            # A cópia vai inteira num arquivo só, sem depender de -wal/-shm ao lado.
            copia.execute("PRAGMA journal_mode = DELETE")
        finally:
            copia.close()
    finally:
        fonte.close()
    if resultado != "ok":
        temporario.unlink(missing_ok=True)
        raise ValueError(f"A cópia não passou na conferência do SQLite: {resultado}")
    temporario.replace(destino)
    _limpar(pasta, manter)
    return destino


def listar_backups(pasta=None):
    pasta = Path(pasta) if pasta is not None else PASTA_PADRAO
    if not pasta.is_dir():
        return []
    # O nome traz data e hora no formato que ordena certo como texto.
    return sorted(pasta.glob(f"{PREFIXO}*.db"))


def _limpar(pasta, manter):
    antigos = listar_backups(pasta)[:-manter]
    for arquivo in antigos:
        arquivo.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Copia o banco do Radar para a pasta backups.")
    parser.add_argument("--manter", type=int, default=MANTER_PADRAO,
                        help=f"quantas cópias guardar (padrão: {MANTER_PADRAO})")
    args = parser.parse_args(argv)
    try:
        destino = fazer_backup(manter=args.manter)
    except ValueError as erro:
        print(erro)
        return 1
    print(f"Backup salvo em {destino}. Cópias guardadas: {len(listar_backups(destino.parent))}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
