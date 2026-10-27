from dataclasses import replace
from decimal import Decimal as D

import pytest

from radar.margem import Parametros, calcular, preco_minimo
from radar.margem.configuracao import obter_configuracao, salvar_configuracao
from radar.valores import centavos, decimal_texto, dinheiro_texto, percentual, reais


@pytest.fixture
def parametros(db):
    return obter_configuracao(db).parametros


def test_exemplo_obrigatorio(parametros):
    resultado = calcular(D("59.90"), D("20.00"), parametros)
    assert resultado.contribuicao == D("14.33")
    assert percentual(resultado.margem_pct) == "23,9%"
    assert preco_minimo(D("20"), parametros) == D("55.56")


def test_preco_zero(parametros):
    with pytest.raises(ValueError, match="maior que zero"):
        calcular(D(0), D(20), parametros)


def test_margem_negativa(parametros):
    resultado = calcular(D(20), D(20), parametros)
    assert resultado.contribuicao == D("-15.20")
    assert resultado.margem_pct == D("-0.76")


@pytest.mark.parametrize("alvo", ["0.74", "0.90"])
def test_preco_inexistente(parametros, alvo):
    with pytest.raises(ValueError, match="Não existe preço mínimo"):
        preco_minimo(D(20), replace(parametros, margem_alvo_pct=D(alvo)))


def test_arredondar_minimo_para_cima_garante_alvo(parametros):
    minimo = preco_minimo(D(20), parametros)
    assert calcular(minimo, D(20), parametros).margem_pct >= parametros.margem_alvo_pct
    assert calcular(minimo - D("0.01"), D(20), parametros).margem_pct < parametros.margem_alvo_pct


def test_margem_nao_e_arredondada_para_aprovar(parametros):
    # Comissão e despesas zero: 19,999% aparece como 20,0%, mas não atinge 20%.
    p = Parametros(D(0), D(0), D("0.20"), D(0), D(0), D(0))
    resultado = calcular(D(1000), D("800.01"), p)
    assert percentual(resultado.margem_pct) == "20,0%"
    assert resultado.margem_pct < p.margem_alvo_pct


@pytest.mark.parametrize("valor", [1.5, D("NaN"), D("Infinity"), D(-1)])
def test_dinheiro_invalido(parametros, valor):
    with pytest.raises(ValueError):
        calcular(valor, D(20), parametros)
    with pytest.raises(ValueError):
        preco_minimo(valor, parametros)


@pytest.mark.parametrize("campo,valor", [("comissao_pct", D("1.01")), ("tributo_pct", D(-1)),
    ("margem_alvo_pct", D("NaN")), ("tarifa_fixa", D("1.001")), ("embalagem", 2.5)])
def test_parametros_invalidos(parametros, campo, valor):
    with pytest.raises(ValueError):
        replace(parametros, **{campo: valor})


def test_configuracao_persistida_e_aplicada(parametros, db):
    novos = replace(parametros, comissao_pct=D("0.10"), tarifa_fixa=D("1.25"))
    salvar_configuracao(novos, 30, db)
    config = obter_configuracao(db)
    assert config.parametros == novos
    assert config.limite_cotacao_dias == 30
    assert calcular(D("59.90"), D(20), config.parametros).contribuicao == D("23.57")


@pytest.mark.parametrize("dias", [0, 3651, 1.5, True])
def test_limite_invalido(parametros, db, dias):
    with pytest.raises(ValueError):
        salvar_configuracao(parametros, dias, db)


@pytest.mark.parametrize("texto,esperado", [("20,00", "20"), ("1.234,56", "1234.56"),
    ("59.90", "59.90"), ("0", "0")])
def test_entrada_monetaria(texto, esperado):
    assert dinheiro_texto(texto) == D(esperado)


@pytest.mark.parametrize("texto", ["NaN", "1,234", "-1,00", "", "texto", "1.2,3", "1e5",
    "1,00000000000000000000000000001"])
def test_entrada_invalida(texto):
    with pytest.raises(ValueError):
        dinheiro_texto(texto)


def test_formatacao_e_centavos():
    assert reais(D("1234.56")) == "R$ 1.234,56"
    assert centavos(D("59.90")) == 5990
    assert decimal_texto("20,5") == D("20.5")
