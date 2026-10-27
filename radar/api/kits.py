"""Rotas da tela de Kits: composição, custo por cotação, plano e estoque por componente.

Custos e necessidade conjunta vêm de `radar.kits`; o planejamento não baixa nem reserva estoque.
"""
from pydantic import BaseModel, StrictInt

from radar.api import protegido, texto
from radar.banco import conectar
from radar.kits import (ajustar_estoque, consultar_kit, listar_kits, necessidade_conjunta, planejar_kits,
    remover_componente, salvar_componente, salvar_kit)
from radar.produtos import listar_produtos
from radar.valores import obrigatorio


class NovoKit(BaseModel):
    nome: str


class PlanoKit(BaseModel):
    nome: str
    quantidade_planejada: StrictInt


class Componente(BaseModel):
    quantidade: StrictInt
    cotacao_id: StrictInt


class Estoque(BaseModel):
    estoque: StrictInt


@protegido.get("/kits")
def kits():
    return {
        "kits": [{c: k[c] for c in ("id", "nome", "quantidade_planejada")} for k in listar_kits()],
        "produtos": [{"id": p["id"], "nome": p["nome"], "estoque_atual": p["estoque_atual"]} for p in listar_produtos()],
        "necessidade": necessidade_conjunta(),
    }


@protegido.post("/kits")
def criar(dados: NovoKit):
    return {"id": salvar_kit(dados.nome)}


@protegido.get("/kits/{kit_id}")
def ficha(kit_id: int):
    with conectar() as c:
        kit = c.execute("SELECT id,nome,quantidade_planejada FROM kit WHERE id=?", (kit_id,)).fetchone()
    if kit is None:
        raise ValueError("Kit não encontrado.")
    kit = dict(kit)
    # Custo de um kit e, se houver plano, do lote planejado (com zero planejado, mostra o de um kit).
    consulta = consultar_kit(kit_id, max(1, kit["quantidade_planejada"]))
    campos = ("produto_id", "produto", "quantidade", "estoque_atual", "custo_unitario_centavos", "codigo",
              "data_cotacao", "sku_fornecedor_id")
    return {**kit, "componentes": [{c: i[c] for c in campos} for i in consulta["componentes"]],
            "custo_unitario": texto(consulta["custo_unitario"]),
            "custo_lote": texto(consulta["custo_lote"]) if kit["quantidade_planejada"] else None}


@protegido.put("/kits/{kit_id}")
def plano(kit_id: int, dados: PlanoKit):
    # Valida o nome antes de gravar o plano, para não salvar só metade da alteração.
    nome = obrigatorio(dados.nome, "o nome do kit")
    with conectar() as c:
        if not c.execute("SELECT 1 FROM kit WHERE id=?", (kit_id,)).fetchone():
            raise ValueError("Kit não encontrado.")
    planejar_kits(kit_id, dados.quantidade_planejada)
    salvar_kit(nome, kit_id)
    return {"id": kit_id}


@protegido.put("/kits/{kit_id}/componentes/{produto_id}")
def componente(kit_id: int, produto_id: int, dados: Componente):
    salvar_componente(kit_id, produto_id, dados.quantidade, dados.cotacao_id)
    return {"ok": True}


@protegido.delete("/kits/{kit_id}/componentes/{produto_id}")
def remover(kit_id: int, produto_id: int):
    remover_componente(kit_id, produto_id)
    return {"ok": True}


@protegido.put("/estoque/{produto_id}")
def estoque(produto_id: int, dados: Estoque):
    ajustar_estoque(produto_id, dados.estoque)
    return {"ok": True}
