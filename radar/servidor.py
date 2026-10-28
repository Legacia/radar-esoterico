"""Sobe a API e a interface: python -m radar.servidor (porta 8501, aceita a rede da casa)."""
import argparse
import sqlite3

import uvicorn

from radar.api import INTERFACE, criar_app
import radar.banco as banco
from radar.backup import fazer_backup


def backup_ao_iniciar():
    """Cópia do banco a cada início do servidor. Falhar no backup avisa, mas não impede o Radar de abrir."""
    if not banco.CAMINHO_PADRAO.is_file():
        return None
    try:
        destino = fazer_backup()
    except (ValueError, OSError, sqlite3.Error) as erro:
        print(f"Aviso: o backup ao iniciar falhou ({erro}). O Radar abre mesmo assim; faça um backup manual.")
        return None
    print(f"Backup do banco salvo em {destino}.")
    return destino


def main(argv=None):
    parser = argparse.ArgumentParser(description="Servidor do Radar Esotérico.")
    parser.add_argument("--endereco", default="0.0.0.0", help="Use 127.0.0.1 para aceitar só este computador.")
    parser.add_argument("--porta", type=int, default=8501)
    parser.add_argument("--sem-backup", action="store_true", help="Não copiar o banco ao iniciar.")
    args = parser.parse_args(argv)
    if not args.sem_backup:
        backup_ao_iniciar()
    if not INTERFACE.is_dir():
        # Sem a interface montada, o endereço abre só a API; avisa como montar em vez de falhar calado.
        print("Aviso: a interface ainda não foi montada. Rode, dentro da pasta web: npm.cmd ci e npm.cmd run build")
    uvicorn.run(criar_app(), host=args.endereco, port=args.porta)


if __name__ == "__main__":
    main()
