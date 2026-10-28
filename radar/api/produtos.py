"""Rotas da tela de Produtos e SKUs: catálogo, ficha do produto e registro de cotações.

Margens e preço mínimo de cada cotação vêm de `linha_sku`, a mesma usada na ficha do fornecedor.
"""
from pydantic import BaseModel, StrictBool, StrictInt

from radar.api import protegido
from radar.api.fornecedores import data_do_texto, linha_sku
from radar.banco import conectar
from radar.fornecedores import listar_fornecedores
from radar.margem.configuracao import obter_configuracao
from radar.produtos import excluir_sku, listar_produtos, listar_skus, registrar_cotacao, salvar_produto
from radar.valores import dinheiro_texto

CAMPOS = ("id", "nome", "familia", "status", "especificacoes_conferidas", "procedencia_conferida",
          "qualidade_conferida", "validado", "estoque_atual")


class Produto(BaseModel):
    nome: str
    familia: str = ""
    status: str = "Candidato"
    especificacoes_conferidas: StrictBool = False
    procedencia_conferida: StrictBool = False
    qualidade_conferida: StrictBool = False


class Cotacao(BaseModel):
    fornecedor_id: StrictInt
    codigo: str
    custo: str
    quantidade_minima: StrictInt
    data: str
    preco_venda: str | None = None


def _produto(p):
    return {c: p[c] for c in CAMPOS}


def _obter(produto_id):
    with conectar() as c:
        linha = c.execute("SELECT * FROM produto WHERE id=?", (produto_id,)).fetchone()
    if linha is None:
        raise ValueError("Produto não encontrado.")
    return dict(linha)


def _salvar(dados, produto_id=None):
    return salvar_produto(dados.nome, dados.familia, dados.status, dados.especificacoes_conferidas,
                          dados.procedencia_conferida, dados.qualidade_conferida, produto_id=produto_id)


@protegido.get("/produtos")
def catalogo():
    return {"produtos": [_produto(p) for p in listar_produtos()],
            # Para o formulário de cotação escolher o fornecedor.
            "fornecedores": [{"id": f["id"], "nome": f["nome"]} for f in listar_fornecedores()]}


@protegido.post("/produtos")
def criar(dados: Produto):
    return {"id": _salvar(dados)}


@protegido.get("/produtos/{produto_id}")
def ficha(produto_id: int):
    produto = _obter(produto_id)
    config = obter_configuracao()
    return {**_produto(produto), "limite_cotacao_dias": config.limite_cotacao_dias,
            "skus": [linha_sku(s, config) for s in listar_skus(produto_id=produto_id)]}


@protegido.put("/produtos/{produto_id}")
def alterar(produto_id: int, dados: Produto):
    return {"id": _salvar(dados, produto_id)}


@protegido.post("/produtos/{produto_id}/cotacoes")
def cotar(produto_id: int, dados: Cotacao):
    preco = dados.preco_venda.strip() if dados.preco_venda else ""
    return {"id": registrar_cotacao(dados.fornecedor_id, produto_id, dados.codigo, dinheiro_texto(dados.custo),
                                    dados.quantidade_minima, data_do_texto(dados.data),
                                    dinheiro_texto(preco) if preco else None)}


@protegido.delete("/cotacoes/{sku_id}")
def excluir_cotacao(sku_id: int, fornecedor_id: int, codigo: str):
    # Fornecedor e código confirmados vão junto, para uma tela antiga não apagar outro SKU com o mesmo id.
    return {"apagadas": excluir_sku(sku_id, fornecedor_id, codigo)}
