"""Rotas da Decisão de compra: orçamento, reserva e os seis critérios de cada produto do lote.

Só planeja e verifica critérios; não faz compras nem movimenta dinheiro. Critérios, valores e o
limite de 20% para produto não validado vêm de `radar.compras.avaliar_lote`.
"""
from decimal import Decimal

from pydantic import BaseModel, StrictBool, StrictInt

from radar.api import CENTAVO, protegido, texto
from radar.compras import avaliar_lote, remover_plano, salvar_orcamento, salvar_plano
from radar.produtos import listar_produtos
from radar.valores import dinheiro_texto, texto_decimal

CAMPOS_ITEM = ("produto_id", "produto", "pronto", "validado", "justificativa_validacao", "acima_vinte", "quantidade",
               "valor_centavos", "fornecedor", "codigo", "data_cotacao", "sku_fornecedor_id", "preco_venda_centavos",
               "demanda_confirmada", "justificativa_demanda", "concorrencia_confirmada", "justificativa_concorrencia")


class Orcamento(BaseModel):
    total: str
    reserva: str


class Plano(BaseModel):
    cotacao_id: StrictInt
    quantidade: StrictInt
    preco_venda: str
    demanda: StrictBool = False
    justificativa_demanda: str = ""
    concorrencia: StrictBool = False
    justificativa_concorrencia: str = ""
    validado: StrictBool = False
    justificativa_validacao: str = ""


def _item(i):
    return {**{c: i[c] for c in CAMPOS_ITEM},
            "criterios": [{"nome": nome, "cumprido": ok} for nome, ok in i["criterios"].items()],
            "percentual_orcamento": texto(i["percentual_orcamento"]),
            "contribuicao": texto(i["contribuicao"]), "margem_pct": texto(i["margem"])}


@protegido.get("/compras")
def lote():
    r = avaliar_lote()
    orcamento = r["orcamento"]
    livre = orcamento["total_centavos"] - orcamento["reserva_centavos"]
    # Uso do valor disponível (orçamento menos reserva), em pontos inteiros de 0 a 100, só para a barra.
    uso = min(100, r["comprometido_centavos"] * 100 // livre) if livre > 0 else 100
    return {
        "orcamento": {"total_centavos": orcamento["total_centavos"], "reserva_centavos": orcamento["reserva_centavos"]},
        "campos_orcamento": {"total": texto_decimal((Decimal(orcamento["total_centavos"]) / 100).quantize(CENTAVO)),
                             "reserva": texto_decimal((Decimal(orcamento["reserva_centavos"]) / 100).quantize(CENTAVO))},
        "comprometido_centavos": r["comprometido_centavos"],
        "disponivel_centavos": r["disponivel_centavos"],
        "excede_disponivel": r["excede_disponivel"],
        "uso_pct": uso,
        "itens": [_item(i) for i in r["itens"]],
        "produtos": [{"id": p["id"], "nome": p["nome"], "validado": p["validado"],
                      "justificativa_validacao": p["justificativa_validacao"]} for p in listar_produtos()],
    }


@protegido.put("/compras/orcamento")
def orcamento(dados: Orcamento):
    salvar_orcamento(dinheiro_texto(dados.total), dinheiro_texto(dados.reserva))
    return {"ok": True}


@protegido.put("/compras/plano/{produto_id}")
def plano(produto_id: int, dados: Plano):
    salvar_plano(produto_id, dados.cotacao_id, dados.quantidade, dinheiro_texto(dados.preco_venda),
                 dados.demanda, dados.justificativa_demanda, dados.concorrencia, dados.justificativa_concorrencia,
                 dados.validado, dados.justificativa_validacao)
    return {"ok": True}


@protegido.delete("/compras/plano/{produto_id}")
def retirar(produto_id: int):
    remover_plano(produto_id)
    return {"ok": True}
