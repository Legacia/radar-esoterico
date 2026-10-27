"""Rota da tela Importar: recebe o CSV como corpo da requisição e devolve o relatório por linha.

O arquivo chega cru (sem formulário multipart), para não depender de outra biblioteca; o limite de
tamanho evita que um arquivo enorme trave o servidor.
"""
from fastapi import Request
from starlette.concurrency import run_in_threadpool

from radar.api import protegido
from radar.importacao import importar_csv

LIMITE_BYTES = 5 * 1024 * 1024


@protegido.post("/importar")
async def importar(request: Request):
    conteudo = await request.body()
    if not conteudo:
        raise ValueError("Escolha um arquivo CSV.")
    if len(conteudo) > LIMITE_BYTES:
        raise ValueError("Arquivo grande demais: o limite é 5 MB. Divida o CSV em partes.")
    # Ler, validar e gravar o CSV leva tempo: roda numa thread de trabalho para o servidor continuar
    # atendendo a outra pessoa enquanto isso. Só a leitura do corpo fica no laço assíncrono.
    relatorio = await run_in_threadpool(importar_csv, conteudo)
    return {"importadas": relatorio.importadas, "repetidas": relatorio.repetidas, "erros": relatorio.erros}
