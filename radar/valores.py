"""Entrada e apresentação brasileiras, sem converter dinheiro para float."""
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re

from radar.margem import validar_decimal


def decimal_texto(texto):
    texto = texto.strip()
    if not re.fullmatch(r"(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d+)?|\d+\.\d+", texto):
        raise ValueError("Informe um número, por exemplo 20,00 ou 1.234,56.")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", texto):
        texto = texto.replace(".", "")
    try:
        valor = Decimal(texto)
    except InvalidOperation as erro:
        raise ValueError("Informe um número válido.") from erro
    validar_decimal(valor, "Valor")
    if valor > Decimal("90000000000000000"):
        raise ValueError("Valor fora do limite permitido.")
    return valor


def centavos(valor):
    validar_decimal(valor, "Valor")
    if valor.as_tuple().exponent < -2 and valor != valor.quantize(Decimal("0.01")):
        raise ValueError("Valores em reais devem ter no máximo duas casas decimais.")
    total = valor * 100
    if total != total.to_integral_value():
        raise ValueError("Valores em reais devem ter no máximo duas casas decimais.")
    if total > 9223372036854775807:
        raise ValueError("Valor fora do limite do banco.")
    return int(total)


def dinheiro_texto(texto):
    return Decimal(centavos(decimal_texto(texto))) / 100


def reais(valor):
    valor = valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return "R$ " + f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def percentual(valor):
    numero = (valor * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return f"{numero:.1f}".replace(".", ",") + "%"


def data_br(valor):
    return date.fromisoformat(valor).strftime("%d/%m/%Y") if valor else "Não informada"


def texto_decimal(valor):
    return format(valor, "f").replace(".", ",")


def data_iso(valor):
    if type(valor) is not date:
        raise ValueError("Informe uma data válida.")
    return valor.isoformat()


def obrigatorio(valor, nome):
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"Informe {nome}.")
    return valor.strip()
