"""Rotas dos itens de apoio (embalagens, caixas, sacolas) e da indicação deles em produtos e kits.

A embalagem resultante e as margens são calculadas em radar/; a tela só mostra.
"""
from pydantic import BaseModel, StrictInt

from radar.api import protegido
from radar.api.fornecedores import data_do_texto
from radar.apoio import excluir_item, indicar, itens_de, listar_itens, retirar, salvar_item
from radar.fornecedores import listar_fornecedores
from radar.valores import dinheiro_texto


class Item(BaseModel):
    nome: str
    fornecedor_id: StrictInt | None = None
    custo: str
    data: str


class Indicacao(BaseModel):
    quantidade: StrictInt


def apoio_de(tipo, destino_id):
    """Itens indicados e a embalagem que vale na conta (None quando vale a padrão)."""
    r = itens_de(tipo, destino_id)
    return {"itens": r["itens"],
            "embalagem_centavos": r["embalagem_centavos"]}


def _salvar(dados, item_id=None):
    return salvar_item(dados.nome, dados.fornecedor_id, dinheiro_texto(dados.custo), data_do_texto(dados.data), item_id)


@protegido.get("/apoio")
def lista():
    return {"itens": listar_itens(),
            "fornecedores": [{"id": f["id"], "nome": f["nome"]} for f in listar_fornecedores()]}


@protegido.post("/apoio")
def criar(dados: Item):
    return {"id": _salvar(dados)}


@protegido.put("/apoio/{item_id}")
def alterar(item_id: int, dados: Item):
    return {"id": _salvar(dados, item_id)}


@protegido.delete("/apoio/{item_id}")
def excluir(item_id: int, nome: str):
    # O nome confirmado vai junto, para uma tela antiga não apagar outro item com o mesmo id.
    excluir_item(item_id, nome)
    return {"ok": True}


@protegido.put("/produtos/{produto_id}/apoio/{item_id}")
def indicar_produto(produto_id: int, item_id: int, dados: Indicacao):
    indicar("produto", produto_id, item_id, dados.quantidade)
    return {"ok": True}


@protegido.delete("/produtos/{produto_id}/apoio/{item_id}")
def retirar_produto(produto_id: int, item_id: int):
    retirar("produto", produto_id, item_id)
    return {"ok": True}


@protegido.put("/kits/{kit_id}/apoio/{item_id}")
def indicar_kit(kit_id: int, item_id: int, dados: Indicacao):
    indicar("kit", kit_id, item_id, dados.quantidade)
    return {"ok": True}


@protegido.delete("/kits/{kit_id}/apoio/{item_id}")
def retirar_kit(kit_id: int, item_id: int):
    retirar("kit", kit_id, item_id)
    return {"ok": True}
