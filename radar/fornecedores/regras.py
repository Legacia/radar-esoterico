"""Checklist puro: resultado explica cada impedimento, sem promover sozinho."""
from decimal import Decimal

ETAPAS = ("Descoberto", "Em contato", "Cotado", "Em avaliação",
          "Fornecedor oficial", "Descartado ou pausado")


def validar_etapa(etapa, motivo=""):
    if etapa not in ETAPAS:
        raise ValueError("Etapa inválida.")
    if etapa == "Descartado ou pausado" and not motivo.strip():
        raise ValueError("Informe o motivo para descartar ou pausar.")


def checklist_promocao(fornecedor, margens_por_produto, alvo):
    # Piso de 20% aprovado pelo usuário; o alvo maior prevalece.
    # Três produtos distintos, não três códigos (decisão do Legacia em 26/10/2026).
    minimo = max(Decimal("0.20"), alvo)
    qualificados = sum(1 for margem in margens_por_produto.values()
                       if margem is not None and margem > 0 and margem >= minimo)
    return {
        "Fornecedor ativo": fornecedor["status"] != "Descartado ou pausado",
        "CNPJ informado e verificado": bool(fornecedor["cnpj"] and fornecedor["cnpj_verificado"]),
        "Condições comerciais verificadas": bool(fornecedor["condicoes_verificadas"]
            and fornecedor["prazo"] and fornecedor["condicao_pagamento"]),
        "Emite nota fiscal": bool(fornecedor["emite_nota"]),
        "Amostra avaliada pela Anna (especificações, procedência e qualidade)": bool(fornecedor["amostra_avaliada"]),
        "Margem no alvo em pelo menos três produtos distintos": qualificados >= 3,
        "Reposição confirmada": bool(fornecedor["reposicao_confirmada"]),
    }
