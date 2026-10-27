"""Planejamento do lote: critérios explicáveis, sem executar compras."""
from decimal import Decimal

from radar.banco import conectar
from radar.margem import calcular
from radar.margem.configuracao import _ler
from radar.valores import centavos


def _orcamento(c):
    return dict(c.execute("SELECT * FROM orcamento WHERE id=1").fetchone())


def obter_orcamento(caminho=None):
    with conectar(caminho) as c:
        return _orcamento(c)


def salvar_orcamento(total, reserva, caminho=None):
    total_centavos, reserva_centavos = centavos(total), centavos(reserva)
    if total_centavos <= 0 or reserva_centavos > total_centavos:
        raise ValueError("O orçamento deve ser positivo e a reserva deve ficar entre zero e o orçamento.")
    with conectar(caminho) as c:
        c.execute("UPDATE orcamento SET total_centavos=?,reserva_centavos=? WHERE id=1", (total_centavos, reserva_centavos))


def criterios_compra(item, parametros, total_comprometido, orcamento, reserva):
    """Função pura. Entradas monetárias em centavos inteiros; margem em Decimal."""
    custo = Decimal(item["custo_unitario_centavos"]) / 100
    resultado = calcular(Decimal(item["preco_venda_centavos"]) / 100, custo, parametros)
    valor = item["quantidade"] * item["custo_unitario_centavos"]
    acima_vinte = not item["validado"] and valor * 100 > orcamento * 20
    criterios = {
        "Fornecedor": bool(item["status_fornecedor"] != "Descartado ou pausado" and item["cnpj"]
            and item["cnpj_verificado"] and item["condicoes_verificadas"] and item["emite_nota"]
            and item["prazo"] and item["condicao_pagamento"]),
        "Produto": bool(item["especificacoes_conferidas"] and item["procedencia_conferida"] and item["qualidade_conferida"]),
        "Margem": resultado.margem_pct > 0 and resultado.margem_pct >= max(Decimal("0.20"), parametros.margem_alvo_pct),
        "Demanda": bool(item["demanda_confirmada"] and item["justificativa_demanda"].strip()),
        "Concorrência": bool(item["concorrencia_confirmada"] and item["justificativa_concorrencia"].strip()),
        "Estoque": (item["quantidade"] >= item["quantidade_minima"] and not acima_vinte
                     and total_comprometido <= orcamento - reserva),
    }
    return {"criterios": criterios, "pronto": all(criterios.values()), "acima_vinte": acima_vinte,
            "valor_centavos": valor, "percentual_orcamento": Decimal(valor) / orcamento,
            "margem": resultado.margem_pct, "contribuicao": resultado.contribuicao}


def _itens(c):
    return [dict(r) for r in c.execute("""SELECT pc.*,p.nome AS produto,p.validado,p.justificativa_validacao,
        p.especificacoes_conferidas,p.procedencia_conferida,p.qualidade_conferida,
        s.codigo,s.custo_unitario_centavos,s.quantidade_minima,s.data_cotacao,s.fornecedor_id,
        f.nome AS fornecedor,f.status AS status_fornecedor,f.cnpj,f.cnpj_verificado,
        f.condicoes_verificadas,f.emite_nota,f.prazo,f.condicao_pagamento
        FROM plano_compra pc JOIN produto p ON p.id=pc.produto_id
        JOIN sku_fornecedor s ON s.id=pc.sku_fornecedor_id
        JOIN fornecedor f ON f.id=s.fornecedor_id ORDER BY p.nome,p.id""")]


def _avaliar(c):
    itens = _itens(c)
    orcamento = _orcamento(c)
    total = sum(i["quantidade"] * i["custo_unitario_centavos"] for i in itens)
    p = _ler(c).parametros
    for item in itens:
        item.update(criterios_compra(item, p, total, orcamento["total_centavos"], orcamento["reserva_centavos"]))
    return {"itens": itens, "orcamento": orcamento, "comprometido_centavos": total,
            "disponivel_centavos": orcamento["total_centavos"] - orcamento["reserva_centavos"] - total,
            "excede_disponivel": total > orcamento["total_centavos"] - orcamento["reserva_centavos"]}


def avaliar_lote(caminho=None):
    with conectar(caminho) as c:
        return _avaliar(c)


def salvar_plano(produto_id, cotacao_id, quantidade, preco_venda, demanda=False,
                  justificativa_demanda="", concorrencia=False, justificativa_concorrencia="",
                  validado=False, justificativa_validacao="", caminho=None):
    if type(quantidade) is not int or not 1 <= quantidade <= 9223372036854775807:
        raise ValueError("A quantidade deve ser um inteiro positivo dentro do limite do banco.")
    preco_centavos = centavos(preco_venda)
    if preco_centavos <= 0:
        raise ValueError("O preço conservador deve ser positivo.")
    for confirmado, justificativa, nome in ((demanda, justificativa_demanda, "demanda"),
        (concorrencia, justificativa_concorrencia, "concorrência"), (validado, justificativa_validacao, "validação do produto")):
        if confirmado and not justificativa.strip():
            raise ValueError(f"Informe a justificativa de {nome}.")
    with conectar(caminho) as c:
        c.execute("BEGIN IMMEDIATE")
        cotacao = c.execute("SELECT * FROM sku_fornecedor WHERE id=? AND produto_id=?", (cotacao_id, produto_id)).fetchone()
        if not cotacao:
            raise ValueError("A cotação deve pertencer ao produto selecionado.")
        # Não deixar a multiplicação extrapolar os valores monetários suportados.
        if quantidade * cotacao["custo_unitario_centavos"] > 9223372036854775807:
            raise ValueError("Valor do lote fora do limite do banco.")
        c.execute("""INSERT INTO plano_compra(produto_id,sku_fornecedor_id,quantidade,preco_venda_centavos,
            demanda_confirmada,justificativa_demanda,concorrencia_confirmada,justificativa_concorrencia)
            VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(produto_id) DO UPDATE SET
            sku_fornecedor_id=excluded.sku_fornecedor_id,quantidade=excluded.quantidade,
            preco_venda_centavos=excluded.preco_venda_centavos,demanda_confirmada=excluded.demanda_confirmada,
            justificativa_demanda=excluded.justificativa_demanda,concorrencia_confirmada=excluded.concorrencia_confirmada,
            justificativa_concorrencia=excluded.justificativa_concorrencia""",
            (produto_id,cotacao_id,quantidade,preco_centavos,bool(demanda),justificativa_demanda.strip(),
             bool(concorrencia),justificativa_concorrencia.strip()))
        c.execute("UPDATE produto SET validado=?,justificativa_validacao=? WHERE id=?",
                  (bool(validado),justificativa_validacao.strip(),produto_id))


def remover_plano(produto_id, caminho=None):
    with conectar(caminho) as c:
        c.execute("DELETE FROM plano_compra WHERE produto_id=?", (produto_id,))
