"""Sobe a API e a interface: python -m radar.servidor (porta 8501, aceita a rede da casa)."""
import argparse

import uvicorn

from radar.api import criar_app


def main(argv=None):
    parser = argparse.ArgumentParser(description="Servidor do Radar Esotérico.")
    parser.add_argument("--endereco", default="0.0.0.0", help="Use 127.0.0.1 para aceitar só este computador.")
    parser.add_argument("--porta", type=int, default=8501)
    args = parser.parse_args(argv)
    uvicorn.run(criar_app(), host=args.endereco, port=args.porta)


if __name__ == "__main__":
    main()
