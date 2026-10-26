"""Fórmulas puras, sem interface nem valores comerciais embutidos."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

CENTAVO = Decimal("0.01")


def validar_decimal(valor, nome, *, percentual=False):
    if not isinstance(valor, Decimal) or not valor.is_finite() or valor < 0:
        raise ValueError(f"{nome}: informe um Decimal finito e não negativo.")
    if percentual and valor > 1:
        raise ValueError(f"{nome}: o percentual deve estar entre 0% e 100%.")


@dataclass(frozen=True)
class Parametros:
    comissao_pct: Decimal
    tributo_pct: Decimal
    margem_alvo_pct: Decimal
    tarifa_fixa: Decimal
    embalagem: Decimal
    outros: Decimal

    def __post_init__(self):
        for campo in ("comissao_pct", "tributo_pct", "margem_alvo_pct"):
            validar_decimal(getattr(self, campo), campo, percentual=True)
        for campo in ("tarifa_fixa", "embalagem", "outros"):
            valor = getattr(self, campo)
            validar_decimal(valor, campo)
            if valor != valor.quantize(CENTAVO):
                raise ValueError(f"{campo}: use no máximo duas casas decimais.")


@dataclass(frozen=True)
class ResultadoMargem:
    contribuicao: Decimal
    margem_pct: Decimal


def calcular(preco, custo, parametros):
    validar_decimal(preco, "Preço")
    validar_decimal(custo, "Custo")
    if preco == 0:
        raise ValueError("O preço de venda deve ser maior que zero para calcular a margem.")
    contribuicao = (preco - custo - preco * parametros.comissao_pct
                    - parametros.tarifa_fixa - parametros.embalagem
                    - preco * parametros.tributo_pct - parametros.outros)
    # Comparações usam a razão sem arredondamento. Reais são exibidos em centavos.
    return ResultadoMargem(contribuicao.quantize(CENTAVO, rounding=ROUND_HALF_UP), contribuicao / preco)


def preco_minimo(custo, parametros):
    validar_decimal(custo, "Custo")
    denominador = 1 - parametros.comissao_pct - parametros.tributo_pct - parametros.margem_alvo_pct
    if denominador <= 0:
        raise ValueError("Não existe preço mínimo com esses percentuais: a soma de comissão, tributo e alvo deve ser menor que 100%.")
    valor = (custo + parametros.tarifa_fixa + parametros.embalagem + parametros.outros) / denominador
    return valor.quantize(CENTAVO, rounding=ROUND_CEILING)
