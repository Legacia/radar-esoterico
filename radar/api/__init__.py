"""API do Radar: rotas finas sobre as regras de radar/, todas protegidas por sessão, exceto entrar.

Dinheiro sai como texto decimal ("14.33") ou centavos inteiros; percentuais como fração em texto
("0.239..."). A formatação brasileira fica para a interface.
"""
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from radar.api.sessao import COOKIE, Sessoes, apagar_cookie, exigir_sessao, gravar_cookie
from radar.banco import inicializar
from radar.compras import obter_orcamento
from radar.margem import calcular, preco_minimo
from radar.margem.configuracao import obter_configuracao
from radar.painel import obter_painel
from radar.usuarios import autenticar
from radar.valores import dinheiro_texto

INTERFACE = Path(__file__).resolve().parents[2] / "web" / "dist"


class Entrada(BaseModel):
    email: str
    senha: str


class Simulacao(BaseModel):
    preco: str
    custo: str


def _texto(valor):
    return None if valor is None else format(valor, "f")


def _parametros(p):
    return {"comissao_pct": _texto(p.comissao_pct), "tributo_pct": _texto(p.tributo_pct),
            "margem_alvo_pct": _texto(p.margem_alvo_pct), "tarifa_fixa": _texto(p.tarifa_fixa),
            "embalagem": _texto(p.embalagem), "outros": _texto(p.outros)}


publico = APIRouter(prefix="/api")
protegido = APIRouter(prefix="/api", dependencies=[Depends(exigir_sessao)])


@publico.post("/entrar")
def entrar(dados: Entrada, request: Request, response: Response):
    # Sem bloqueio por tentativas erradas (decisão do Legacia em 27/10/2026).
    usuario = autenticar(dados.email, dados.senha)
    if usuario is None:
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")
    sessoes = request.app.state.sessoes
    # Uma sessão nova a cada entrada; a anterior deste navegador deixa de valer.
    sessoes.fechar(request.cookies.get(COOKIE))
    gravar_cookie(response, sessoes.abrir(usuario))
    return usuario


@protegido.post("/sair")
def sair(request: Request, response: Response):
    request.app.state.sessoes.fechar(request.cookies.get(COOKIE))
    apagar_cookie(response)
    return {"ok": True}


@protegido.get("/eu")
def eu(usuario: dict = Depends(exigir_sessao)):
    return usuario


@protegido.get("/painel")
def painel():
    dados = obter_painel()
    dados["orcamento_total_centavos"] = obter_orcamento()["total_centavos"]
    return dados


@protegido.get("/configuracao")
def configuracao():
    config = obter_configuracao()
    return {"parametros": _parametros(config.parametros), "limite_cotacao_dias": config.limite_cotacao_dias}


@protegido.post("/calculadora/simular")
def simular(dados: Simulacao):
    p = obter_configuracao().parametros
    custo = dinheiro_texto(dados.custo)
    resultado = calcular(dinheiro_texto(dados.preco), custo, p)
    try:
        minimo, aviso = preco_minimo(custo, p), None
    except ValueError as erro:
        minimo, aviso = None, str(erro)
    return {"contribuicao": _texto(resultado.contribuicao), "margem_pct": _texto(resultado.margem_pct),
            "preco_minimo": _texto(minimo), "aviso_preco_minimo": aviso}


def criar_app():
    inicializar()
    # Sem /docs nem /openapi.json: o Radar não publica a lista de rotas.
    app = FastAPI(title="Radar Esotérico", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.sessoes = Sessoes()

    @app.exception_handler(ValueError)
    def erro_de_regra(request, erro):
        # As regras de radar/ explicam o problema em português; a tela mostra a mensagem.
        return JSONResponse(status_code=400, content={"detail": str(erro)})

    app.include_router(publico)
    app.include_router(protegido)
    if INTERFACE.is_dir():
        app.mount("/", StaticFiles(directory=INTERFACE, html=True), name="interface")
    return app
