"""Rotas da Pesquisa de oportunidades: anúncios, preços observados e margem por anúncio.

Simulação livre (decisão do Legacia em 27/10/2026): usa a margem-alvo configurada, mesmo abaixo de 20%.
Margens, mediana e preço mínimo vêm de `radar.mercado.pesquisar`; a tela só mostra.
"""
from decimal import Decimal

from pydantic import BaseModel, StrictInt

from radar.api import protegido, texto
from radar.api.fornecedores import data_do_texto
from radar.margem.configuracao import obter_configuracao
from radar.mercado import listar_anuncios, listar_cotacoes, pesquisar, registrar_anuncio, vincular_produto
from radar.produtos import cotacao_antiga, listar_produtos
from radar.valores import dinheiro_texto


class Anuncio(BaseModel):
    marketplace: str
    titulo: str
    url: str
    preco: str
    data: str
    produto_id: StrictInt | None = None
    sinal: str = ""


class Vinculo(BaseModel):
    produto_id: StrictInt | None = None


@protegido.get("/pesquisa/anuncios")
def anuncios():
    return {
        "anuncios": [{c: a[c] for c in ("id", "marketplace", "titulo", "url", "produto_id", "produto")}
                     for a in listar_anuncios()],
        "produtos": [{"id": p["id"], "nome": p["nome"]} for p in listar_produtos()],
    }


@protegido.post("/pesquisa/anuncios")
def novo_anuncio(dados: Anuncio):
    anuncio_id, novo_preco = registrar_anuncio(dados.marketplace, dados.titulo, dados.url, dinheiro_texto(dados.preco),
                                               data_do_texto(dados.data), dados.produto_id, dados.sinal)
    # novo_preco falso: o mesmo preço na mesma data já existia e foi preservado sem duplicar.
    return {"anuncio_id": anuncio_id, "novo_preco": novo_preco}


@protegido.put("/pesquisa/anuncios/{anuncio_id}/produto")
def vincular(anuncio_id: int, dados: Vinculo):
    vincular_produto(anuncio_id, dados.produto_id)
    return {"ok": True}


@protegido.get("/pesquisa/cotacoes")
def cotacoes(produto_id: int):
    return [{"id": c["id"], "fornecedor": c["fornecedor"], "codigo": c["codigo"], "data_cotacao": c["data_cotacao"],
             "custo_centavos": c["custo_unitario_centavos"], "quantidade_minima": c["quantidade_minima"],
             "preco_venda_centavos": c["preco_venda_centavos"]} for c in listar_cotacoes(produto_id)]


@protegido.get("/pesquisa")
def resultado(produto_id: int, cotacao_id: int, marketplace: str = "", termo: str = ""):
    r = pesquisar(produto_id, cotacao_id, marketplace, termo)
    config = obter_configuracao()
    linhas = [{"id": l["id"], "marketplace": l["marketplace"], "titulo": l["titulo"], "url": l["url"],
               "sinal": l["sinal"], "preco_centavos": l["preco_centavos"], "data": l["data"],
               "contribuicao": texto(l["contribuicao"]), "margem_pct": texto(l["margem"])} for l in r["linhas"]]
    marketplaces = sorted({a["marketplace"] for a in listar_anuncios() if a["produto_id"] == produto_id})
    return {
        "linhas": linhas,
        "historico": r["historico"],
        "mediana": texto(r["mediana"]),
        "preco_minimo": texto(r["preco_minimo"]),
        "no_alvo": r["no_alvo"],
        "margem_alvo_pct": texto(config.parametros.margem_alvo_pct),
        "custo_centavos": int(r["custo"] * 100),
        "data_cotacao": r["data_cotacao"],
        "embalagem": texto(r["embalagem"].quantize(Decimal("0.01"))),
        "cotacao_antiga": cotacao_antiga(r["data_cotacao"], config.limite_cotacao_dias),
        "marketplaces": marketplaces,
    }
