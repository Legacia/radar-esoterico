from datetime import date, timedelta
from decimal import Decimal as D
from pathlib import Path

import pytest

from radar.banco import conectar
from radar.importacao import importar_csv
from radar.mercado import (listar_anuncios, mediana_precos, pesquisar, registrar_anuncio, vincular_produto)
from radar.produtos import registrar_cotacao, salvar_produto
from radar.valores import reais
from tests.apoio_bloco3 import criar_base

CABECALHO = "marketplace;titulo;url;preco;data;produto;sinal\n"


def linha(url="https://example.invalid/a", preco="59,90", data=None, produto="", sinal="em alta"):
    return f"Mercado fictício;Título fictício;{url};{preco};{data or date.today().isoformat()};{produto};{sinal}\n"


def test_importa_exemplo_duas_vezes_sem_duplicar(db):
    conteudo = (Path(__file__).resolve().parents[1] / "exemplos/anuncios_ficticios.csv").read_bytes()
    primeiro = importar_csv(conteudo,db)
    segundo = importar_csv(conteudo,db)
    assert (primeiro.importadas,primeiro.repetidas,primeiro.erros) == (3,0,[])
    assert (segundo.importadas,segundo.repetidas,segundo.erros) == (0,3,[])
    with conectar(db) as c:
        assert c.execute("SELECT count(*) FROM anuncio").fetchone()[0] == 3
        assert c.execute("SELECT count(*) FROM preco_observado").fetchone()[0] == 3


def test_linhas_ruins_nao_impedem_as_boas_e_relatorio_tem_numero(db):
    conteudo = CABECALHO + linha() + linha(preco="NaN") + linha(data="não-data")
    conteudo += linha(url="javascript:algo") + linha(produto="Inexistente")
    conteudo += "campos;faltando\n" + linha(url="https://example.invalid/b")
    r = importar_csv(conteudo,db)
    assert r.importadas == 2
    assert [e["linha"] for e in r.erros] == [3,4,5,6,7]
    assert len(listar_anuncios(db)) == 2


def test_importa_utf8_bom_e_nome_de_produto(db):
    _,produto,_ = criar_base(db)
    r = importar_csv((CABECALHO + linha(produto="PRODUTO FICTÍCIO A")).encode("utf-8-sig"),db)
    assert r.importadas == 1
    assert listar_anuncios(db)[0]["produto_id"] == produto


def test_nome_ambiguo_nao_liga_ao_produto_errado(db):
    criar_base(db)
    salvar_produto("produto fictício a","","Candidato",caminho=db)
    r = importar_csv(CABECALHO + linha(produto="Produto fictício A"),db)
    assert r.importadas == 0
    assert "ambíguo" in r.erros[0]["erro"]


@pytest.mark.parametrize("conteudo", [b"\xff", "", "titulo;url\n", "marketplace;titulo;url;preco;data;data\n",
    "marketplace;titulo;url;preco;data;coluna_errada\n"])
def test_formato_invalido(db,conteudo):
    with pytest.raises(ValueError):
        importar_csv(conteudo,db)


def test_estrutura_irrecuperavel_relata_erro_sem_perder_linhas_anteriores(db):
    r = importar_csv(CABECALHO + linha() + '"campo sem fechamento\n',db)
    assert r.importadas == 1
    assert r.erros[0]["linha"] == 3


def test_observacoes_novas_preservam_historico_e_mediana_usa_uma_por_anuncio(db):
    _,produto,cotacao = criar_base(db)
    ontem = date.today() - timedelta(days=1)
    registrar_anuncio("Teste","A fictício","https://example.invalid/a",D(40),ontem,produto,caminho=db)
    registrar_anuncio("TESTE","A fictício","https://example.invalid/a",D("59.90"),date.today(),produto,"em alta",db)
    registrar_anuncio("Teste","B fictício","https://example.invalid/b",D("64.90"),date.today(),produto,caminho=db)
    r = pesquisar(produto,cotacao,caminho=db)
    assert len(r["linhas"]) == 2
    assert len(r["historico"]) == 3
    assert r["mediana"] == D("62.40")
    assert r["no_alvo"] == 2
    assert r["preco_minimo"] == D("55.56")


def test_trocar_cotacao_muda_margens_e_preco_minimo_sem_mudar_sinal(db):
    fornecedor,produto,cotacao = criar_base(db)
    registrar_anuncio("Teste","Fictício","https://example.invalid/a",D("59.90"),date.today(),produto,"mais vendido",db)
    outra = registrar_cotacao(fornecedor,produto,"OUTRA",D(25),1,date.today(),D("59.90"),db)
    a = pesquisar(produto,cotacao,caminho=db)
    b = pesquisar(produto,outra,caminho=db)
    assert a["linhas"][0]["contribuicao"] == D("14.33")
    assert b["linhas"][0]["contribuicao"] == D("9.33")
    assert (a["no_alvo"],b["no_alvo"]) == (1,0)
    assert b["preco_minimo"] > a["preco_minimo"]
    assert a["linhas"][0]["sinal"] == b["linhas"][0]["sinal"] == "mais vendido"


def test_vincular_e_filtrar_anuncios(db):
    _,produto,cotacao = criar_base(db)
    anuncio,_ = registrar_anuncio("Loja fictícia","Cristal fictício","https://example.invalid/a",D(60),date.today(),caminho=db)
    assert pesquisar(produto,cotacao,caminho=db)["linhas"] == []
    vincular_produto(anuncio,produto,db)
    assert len(pesquisar(produto,cotacao,"LOJA FICTÍCIA","CRISTAL",db)["linhas"]) == 1
    assert pesquisar(produto,cotacao,"outro","",db)["linhas"] == []
    assert pesquisar(produto,cotacao,"","incenso",db)["linhas"] == []


def test_cotacao_de_outro_produto_recusada(db):
    _,_,cotacao = criar_base(db)
    outro = salvar_produto("Outro fictício","","Candidato",caminho=db)
    with pytest.raises(ValueError):
        pesquisar(outro,cotacao,caminho=db)


def test_erro_de_vinculo_em_linha_nao_altera_anuncio_anterior(db):
    _,produto,_ = criar_base(db)
    outro = salvar_produto("Outro fictício","","Candidato",caminho=db)
    registrar_anuncio("Mercado fictício","Título original","https://example.invalid/a",D(50),date.today(),produto,caminho=db)
    r = importar_csv(CABECALHO + linha(produto="Outro fictício"),db)
    assert r.importadas == 0 and len(r.erros) == 1
    assert listar_anuncios(db)[0]["titulo"] == "Título original"
    assert listar_anuncios(db)[0]["produto_id"] != outro


@pytest.mark.parametrize("preco,data,url", [(D(0),date.today(),"https://example.invalid/a"),
    (D(50),date.today()+timedelta(days=1),"https://example.invalid/a"),
    (D(50),date.today(),"https://usuario:senha@example.invalid/a")])
def test_anuncio_invalido_recusado(db,preco,data,url):
    with pytest.raises(ValueError):
        registrar_anuncio("Teste","Fictício",url,preco,data,caminho=db)


def test_mediana_exata_e_arredondamento_de_exibicao():
    assert mediana_precos([]) is None
    assert mediana_precos([D(3),D(1),D(2)]) == D(2)
    assert mediana_precos([D("59.90"),D("59.91")]) == D("59.905")
    assert reais(D("59.905")) == "R$ 59,91"


def test_numero_de_linha_considera_linhas_vazias(db):
    r = importar_csv(CABECALHO + "\n" + linha() + "\n" + linha(preco="inválido"),db)
    assert r.importadas == 1
    assert r.erros[0]["linha"] == 5


def test_campo_com_multiplas_linhas_e_erro_recuperavel_preserva_as_demais(db):
    data = date.today().isoformat()
    conteudo = CABECALHO + f'Teste;"Título\nfictício";https://example.invalid/multi;59,90;{data};;\n'
    conteudo += 'Teste;"aspas"erradas;https://example.invalid/erro;59,90;2026-10-26;;\n'
    conteudo += linha(url="https://example.invalid/depois")
    r = importar_csv(conteudo,db)
    assert r.importadas == 2
    assert r.erros[0]["linha"] == 4


def test_mesmo_dia_vale_o_ultimo_preco_novo_e_repetido_nao_volta_a_valer(db):
    _, produto, cotacao = criar_base(db)
    preco = lambda valor: linha(preco=valor, produto="Produto fictício A")
    relatorio = importar_csv(CABECALHO + preco("10,00") + preco("12,00"), db)
    assert (relatorio.importadas, relatorio.repetidas, relatorio.erros) == (2, 0, [])
    r = pesquisar(produto, cotacao, caminho=db)
    assert [l["preco"] for l in r["linhas"]] == [D("12.00")]
    assert len(r["historico"]) == 2
    # Comportamento atual, mantido de propósito: um preço já visto no mesmo dia conta como
    # repetido e não volta a valer, mesmo que seja o último importado.
    relatorio = importar_csv(CABECALHO + preco("10,00"), db)
    assert (relatorio.importadas, relatorio.repetidas) == (0, 1)
    r = pesquisar(produto, cotacao, caminho=db)
    assert [l["preco"] for l in r["linhas"]] == [D("12.00")]
    assert len(r["historico"]) == 2
