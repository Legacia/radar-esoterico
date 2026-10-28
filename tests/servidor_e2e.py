"""Servidor do teste de ponta a ponta (Playwright): API + web/dist com banco temporário e conta fictícia.

Nunca toca data/radar.db. Cada execução começa com um banco vazio, apagado ao terminar.
Uso: python -m tests.servidor_e2e (a partir da raiz do projeto); o Playwright inicia sozinho.
"""
import os
from pathlib import Path
import tempfile

import uvicorn

import radar.banco as banco
from radar.usuarios import criar_usuario

PORTA = int(os.environ.get("RADAR_E2E_PORTA", "8599"))
# Conta fictícia, só existe neste banco temporário.
EMAIL, SENHA = "e2e@example.invalid", "senha-ficticia-e2e"


def main():
    with tempfile.TemporaryDirectory(prefix="radar-e2e-") as pasta:
        caminho = Path(pasta) / "e2e.db"
        banco.CAMINHO_PADRAO = caminho
        banco.inicializar(caminho)
        criar_usuario("Pessoa fictícia E2E", EMAIL, SENHA, caminho)
        from radar.api import criar_app
        uvicorn.run(criar_app(), host="127.0.0.1", port=PORTA, log_level="warning")


if __name__ == "__main__":
    main()
