"""Rotas da tela de Fornecedores: lista, ficha, condições, etapa, promoção e contatos.

Checklist, margens e preço mínimo são calculados aqui, pelas regras de radar/; a tela só mostra.
"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, StrictBool

from radar.api import protegido, texto
from radar.fornecedores import (ETAPAS, alterar_etapa, avaliar_promocao, listar_fornecedores,
    listar_interacoes, obter_fornecedor, promover, registrar_interacao, salvar_fornecedor)
from radar.margem import preco_minimo
from radar.margem.configuracao import obter_configuracao
from radar.produtos import cotacao_antiga, estimar_margem, listar_skus
from radar.valores import dinheiro_texto


class Fornecedor(BaseModel):
    nome: str
    cnpj: str = ""
    contato: str = ""
    pedido_minimo: str = "0"
    prazo: str = ""
    condicao_pagamento: str = ""
    cnpj_verificado: StrictBool = False
    condicoes_verificadas: StrictBool = False
    emite_nota: StrictBool = False
    amostra_avaliada: StrictBool = False
    reposicao_confirmada: StrictBool = False


class Etapa(BaseModel):
    etapa: str
    motivo: str = ""


class Contato(BaseModel):
    data: str
    canal: str
    resumo: str
    situacao_resposta: str | None = None


def linha_sku(sku, config):
    """Cotação atual com margem estimada e preço mínimo para o alvo configurado."""
    margem = estimar_margem(sku, config.parametros)
    try:
        minimo, aviso = preco_minimo(Decimal(sku["custo_unitario_centavos"]) / 100, config.parametros), None
    except ValueError as erro:
        minimo, aviso = None, str(erro)
    return {
        "id": sku["id"], "codigo": sku["codigo"], "produto_id": sku["produto_id"], "produto": sku["produto"],
        "fornecedor_id": sku["fornecedor_id"], "fornecedor": sku["fornecedor"],
        "custo_centavos": sku["custo_unitario_centavos"], "quantidade_minima": sku["quantidade_minima"],
        "data_cotacao": sku["data_cotacao"],
        "cotacao_antiga": cotacao_antiga(sku["data_cotacao"], config.limite_cotacao_dias),
        "preco_venda_centavos": sku["preco_venda_centavos"],
        "contribuicao": texto(margem.contribuicao) if margem else None,
        "margem_pct": texto(margem.margem_pct) if margem else None,
        "preco_minimo": texto(minimo), "aviso_preco_minimo": aviso,
    }


def _resumo(f):
    return {chave: f[chave] for chave in ("id", "nome", "status", "prazo", "condicao_pagamento", "data_ultima_cotacao")}


def _data(valor):
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        raise ValueError("Informe uma data válida.") from None


def _salvar(dados, fornecedor_id=None):
    return salvar_fornecedor(dados.nome, dados.cnpj, dados.contato, dinheiro_texto(dados.pedido_minimo),
        dados.prazo, dados.condicao_pagamento, dados.cnpj_verificado, dados.condicoes_verificadas,
        dados.emite_nota, dados.amostra_avaliada, dados.reposicao_confirmada, fornecedor_id=fornecedor_id)


@protegido.get("/fornecedores")
def lista():
    return {"etapas": list(ETAPAS), "fornecedores": [_resumo(f) for f in listar_fornecedores()]}


@protegido.post("/fornecedores")
def criar(dados: Fornecedor):
    return {"id": _salvar(dados)}


@protegido.get("/fornecedores/{fornecedor_id}")
def ficha(fornecedor_id: int):
    f = obter_fornecedor(fornecedor_id)
    config = obter_configuracao()
    checklist = avaliar_promocao(fornecedor_id)
    campos = ("cnpj", "contato", "pedido_minimo_centavos", "data_oficial", "motivo_descarte", "cnpj_verificado",
              "condicoes_verificadas", "emite_nota", "amostra_avaliada", "reposicao_confirmada")
    return {
        **_resumo(f), **{c: f[c] for c in campos},
        "checklist": [{"item": item, "cumprido": ok} for item, ok in checklist.items()],
        # Mesmo piso usado pela regra de promoção, para a tela explicar a exigência.
        "margem_minima_pct": texto(max(Decimal("0.20"), config.parametros.margem_alvo_pct)),
        "limite_cotacao_dias": config.limite_cotacao_dias,
        "skus": [linha_sku(s, config) for s in listar_skus(fornecedor_id=fornecedor_id)],
        "contatos": listar_interacoes(fornecedor_id),
    }


@protegido.put("/fornecedores/{fornecedor_id}")
def alterar(fornecedor_id: int, dados: Fornecedor):
    return {"id": _salvar(dados, fornecedor_id)}


@protegido.post("/fornecedores/{fornecedor_id}/etapa")
def etapa(fornecedor_id: int, dados: Etapa):
    alterar_etapa(fornecedor_id, dados.etapa, dados.motivo)
    return {"ok": True}


@protegido.post("/fornecedores/{fornecedor_id}/promover")
def promocao(fornecedor_id: int):
    obter_fornecedor(fornecedor_id)
    pendencias = promover(fornecedor_id)
    return {"promovido": not pendencias, "pendencias": pendencias}


@protegido.post("/fornecedores/{fornecedor_id}/contatos")
def contato(fornecedor_id: int, dados: Contato):
    return {"id": registrar_interacao(fornecedor_id, _data(dados.data), dados.canal, dados.resumo,
                                      situacao_resposta=dados.situacao_resposta)}
