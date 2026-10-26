"""Parâmetros compartilhados entre as telas, persistidos no SQLite."""
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import tomllib

from radar.banco import conectar
from radar.margem import Parametros
from radar.valores import centavos


@dataclass(frozen=True)
class Configuracao:
    parametros: Parametros
    limite_cotacao_dias: int


def carregar_padroes():
    with Path(__file__).with_name("padroes.toml").open("rb") as arquivo:
        return tomllib.load(arquivo)


def _ler(conexao):
    padroes = carregar_padroes()
    conexao.execute("""INSERT OR IGNORE INTO configuracao
        (id, comissao_pct, tributo_pct, margem_alvo_pct, tarifa_fixa_centavos,
         embalagem_centavos, outros_centavos, limite_cotacao_dias)
        VALUES (1, :comissao_pct, :tributo_pct, :margem_alvo_pct, :tarifa_fixa_centavos,
                :embalagem_centavos, :outros_centavos, :limite_cotacao_dias)""", padroes)
    linha = conexao.execute("SELECT * FROM configuracao WHERE id=1").fetchone()
    return Configuracao(Parametros(
        Decimal(linha["comissao_pct"]), Decimal(linha["tributo_pct"]), Decimal(linha["margem_alvo_pct"]),
        Decimal(linha["tarifa_fixa_centavos"]) / 100, Decimal(linha["embalagem_centavos"]) / 100,
        Decimal(linha["outros_centavos"]) / 100,
    ), linha["limite_cotacao_dias"])


def obter_configuracao(caminho=None):
    with conectar(caminho) as conexao:
        return _ler(conexao)


def salvar_configuracao(parametros, limite_cotacao_dias, caminho=None):
    if type(limite_cotacao_dias) is not int or not 1 <= limite_cotacao_dias <= 3650:
        raise ValueError("O limite de cotação deve estar entre 1 e 3650 dias.")
    with conectar(caminho) as conexao:
        conexao.execute("""INSERT INTO configuracao VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET comissao_pct=excluded.comissao_pct,
            tributo_pct=excluded.tributo_pct, margem_alvo_pct=excluded.margem_alvo_pct,
            tarifa_fixa_centavos=excluded.tarifa_fixa_centavos,
            embalagem_centavos=excluded.embalagem_centavos, outros_centavos=excluded.outros_centavos,
            limite_cotacao_dias=excluded.limite_cotacao_dias""",
            (str(parametros.comissao_pct), str(parametros.tributo_pct), str(parametros.margem_alvo_pct),
             centavos(parametros.tarifa_fixa), centavos(parametros.embalagem), centavos(parametros.outros),
             limite_cotacao_dias))
