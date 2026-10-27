"""API do Radar: rotas finas sobre as regras de radar/, todas protegidas por sessão, exceto entrar.

Dinheiro sai como texto decimal ("14.33") ou centavos inteiros; percentuais como fração em texto
("0.239..."). A formatação brasileira fica para a interface.
"""
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, StrictBool, StrictInt

from radar.api.sessao import COOKIE, Sessoes, apagar_cookie, exigir_sessao, gravar_cookie
from radar.banco import inicializar
from radar.compras import obter_orcamento
from radar.margem import Parametros, calcular, preco_minimo
from radar.margem.configuracao import obter_configuracao, salvar_configuracao
from radar.painel import obter_painel, salvar_tarefa
from radar.usuarios import autenticar
from radar.valores import decimal_texto, dinheiro_texto, texto_decimal

CENTAVO = Decimal("0.01")
INTERFACE = Path(__file__).resolve().parents[2] / "web" / "dist"


class Entrada(BaseModel):
    email: str
    senha: str


class Tarefa(BaseModel):
    titulo: str
    semana: StrictInt
    responsavel: str
    concluida: StrictBool = False


class Configuracao(BaseModel):
    """Percentuais como o usuário digita ("20" ou "20,5"); valores em reais ("4,50")."""
    comissao: str
    tributo: str
    margem_alvo: str
    tarifa_fixa: str
    embalagem: str
    outros: str
    limite_cotacao_dias: StrictInt


class Simulacao(BaseModel):
    preco: str
    custo: str


def texto(valor):
    return None if valor is None else format(valor, "f")


def _parametros(p):
    return {"comissao_pct": texto(p.comissao_pct), "tributo_pct": texto(p.tributo_pct),
            "margem_alvo_pct": texto(p.margem_alvo_pct), "tarifa_fixa": texto(p.tarifa_fixa),
            "embalagem": texto(p.embalagem), "outros": texto(p.outros)}


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
    total = obter_orcamento()["total_centavos"]
    dados["orcamento_total_centavos"] = total
    # Fração do orçamento já comprometida, em texto decimal; a tela só formata.
    dados["comprometido_pct"] = texto(Decimal(dados["comprometido_centavos"]) / total) if total else None
    return dados


@protegido.post("/tarefas")
def criar_tarefa(dados: Tarefa):
    return {"id": salvar_tarefa(dados.titulo, dados.semana, dados.responsavel, dados.concluida)}


@protegido.put("/tarefas/{tarefa_id}")
def alterar_tarefa(tarefa_id: int, dados: Tarefa):
    return {"id": salvar_tarefa(dados.titulo, dados.semana, dados.responsavel, dados.concluida, tarefa_id)}


@protegido.get("/configuracao")
def configuracao():
    config = obter_configuracao()
    p = config.parametros
    # "campos" traz os valores já no formato dos campos da tela (percentual e reais com vírgula).
    campos = {"comissao": texto_decimal(p.comissao_pct * 100), "tributo": texto_decimal(p.tributo_pct * 100),
              "margem_alvo": texto_decimal(p.margem_alvo_pct * 100), "tarifa_fixa": texto_decimal(p.tarifa_fixa.quantize(CENTAVO)),
              "embalagem": texto_decimal(p.embalagem.quantize(CENTAVO)), "outros": texto_decimal(p.outros.quantize(CENTAVO))}
    return {"parametros": _parametros(p), "campos": campos, "limite_cotacao_dias": config.limite_cotacao_dias}


@protegido.put("/configuracao")
def salvar_parametros(dados: Configuracao):
    novos = Parametros(decimal_texto(dados.comissao) / 100, decimal_texto(dados.tributo) / 100,
                       decimal_texto(dados.margem_alvo) / 100, dinheiro_texto(dados.tarifa_fixa),
                       dinheiro_texto(dados.embalagem), dinheiro_texto(dados.outros))
    salvar_configuracao(novos, dados.limite_cotacao_dias)
    return configuracao()


@protegido.post("/calculadora/simular")
def simular(dados: Simulacao):
    p = obter_configuracao().parametros
    custo = dinheiro_texto(dados.custo)
    resultado = calcular(dinheiro_texto(dados.preco), custo, p)
    try:
        minimo, aviso = preco_minimo(custo, p), None
    except ValueError as erro:
        minimo, aviso = None, str(erro)
    return {"contribuicao": texto(resultado.contribuicao), "margem_pct": texto(resultado.margem_pct),
            "preco_minimo": texto(minimo), "aviso_preco_minimo": aviso}


# Rotas de cada tela, registradas no mesmo roteador protegido.
from radar.api import (fornecedores as _fornecedores, importar as _importar, kits as _kits,  # noqa: E402,F401
                       pesquisa as _pesquisa, produtos as _produtos)


def criar_app():
    inicializar()
    # Sem /docs nem /openapi.json: o Radar não publica a lista de rotas.
    app = FastAPI(title="Radar Esotérico", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.sessoes = Sessoes()

    @app.exception_handler(ValueError)
    def erro_de_regra(request, erro):
        # As regras de radar/ explicam o problema em português; a tela mostra a mensagem.
        return JSONResponse(status_code=400, content={"detail": str(erro)})

    @app.exception_handler(RequestValidationError)
    def formato_invalido(request, erro):
        return JSONResponse(status_code=400, content={"detail": "Dados em formato inválido. Confira os campos."})

    app.include_router(publico)
    app.include_router(protegido)
    if INTERFACE.is_dir():
        app.mount("/", StaticFiles(directory=INTERFACE, html=True), name="interface")
    return app
