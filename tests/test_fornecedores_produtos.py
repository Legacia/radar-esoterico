from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from radar.banco import conectar
from radar.fornecedores import (ETAPAS, alterar_etapa, avaliar_promocao, listar_interacoes,
    obter_fornecedor, promover, registrar_interacao, salvar_fornecedor)
from radar.fornecedores.regras import checklist_promocao, validar_etapa
from radar.margem.configuracao import obter_configuracao, salvar_configuracao
from radar.produtos import (cotacao_antiga, estimar_margem, listar_produtos,
    listar_skus, registrar_cotacao, salvar_produto)


@pytest.fixture
def fornecedor(db):
    return salvar_fornecedor("Fornecedor fictício", "CNPJ fictício verificado manualmente", "Contato fictício",
        D(100), "5 dias", "Pix", True, True, True, True, True, caminho=db)


@pytest.fixture
def produto(db):
    return salvar_produto("Produto fictício", "Incensos", "Candidato", caminho=db)


def tres_skus(fornecedor, produto, db, preco=D("59.90")):
    # A promoção exige três produtos diferentes, não três códigos do mesmo produto.
    produtos = [produto] + [salvar_produto(f"Produto fictício {n}", "", "Candidato", caminho=db) for n in (2, 3)]
    for n, p in enumerate(produtos):
        registrar_cotacao(fornecedor, p, f"SKU-{n}", D(20), 1, date.today(), preco, db)


def test_ciclo_de_vida_e_promocao(fornecedor, produto, db):
    for etapa in ETAPAS[:4]:
        alterar_etapa(fornecedor, etapa, caminho=db)
        assert obter_fornecedor(fornecedor, db)["status"] == etapa
    assert promover(fornecedor, db)  # Sem margem demonstrada, não altera etapa.
    assert obter_fornecedor(fornecedor, db)["status"] == "Em avaliação"
    tres_skus(fornecedor, produto, db)
    assert all(avaliar_promocao(fornecedor, db).values())
    assert promover(fornecedor, db) == []
    f = obter_fornecedor(fornecedor, db)
    assert f["status"] == "Fornecedor oficial"
    assert f["data_oficial"] == date.today().isoformat()
    assert promover(fornecedor, db) == []
    assert obter_fornecedor(fornecedor, db)["data_oficial"] == f["data_oficial"]


def test_nao_promove_pelo_cadastro_ou_troca_etapa(fornecedor, produto, db):
    tres_skus(fornecedor, produto, db)
    assert obter_fornecedor(fornecedor, db)["status"] == "Descoberto"
    with pytest.raises(ValueError, match="promoção"):
        alterar_etapa(fornecedor, "Fornecedor oficial", caminho=db)


@pytest.mark.parametrize("campo", ["cnpj_verificado", "condicoes_verificadas", "emite_nota", "amostra_avaliada", "reposicao_confirmada"])
def test_cada_verificacao_obrigatoria(fornecedor, db, campo):
    f = obter_fornecedor(fornecedor, db)
    f[campo] = 0
    checks = checklist_promocao(f, {str(i): D("0.30") for i in range(3)}, D("0.20"))
    assert not all(checks.values())


@pytest.mark.parametrize("cnpj,prazo,pagamento", [("", "5 dias", "Pix"), ("fictício", "", "Pix"), ("fictício", "5 dias", "")])
def test_dados_basicos_obrigatorios_para_verificar(db, cnpj, prazo, pagamento):
    with pytest.raises(ValueError):
        salvar_fornecedor("Fictício", cnpj, "", D(0), prazo, pagamento, True, True, caminho=db)


@pytest.mark.parametrize("margens", [{"a": D("0.30"), "b": D("0.30")},
    {"a": D("0.30"), "b": D("0.30"), "c": None},
    {"a": D("0.30"), "b": D("0.30"), "c": D("0.19999")}])
def test_pelo_menos_tres_skus_com_margem_exata(fornecedor, db, margens):
    assert not all(checklist_promocao(obter_fornecedor(fornecedor, db), margens, D("0.20")).values())


@pytest.mark.parametrize("alvo,margem,passa", [("0.10", "0.19", False), ("0.10", "0.20", True),
    ("0.30", "0.29", False), ("0.30", "0.30", True)])
def test_alvo_configurado_com_piso_vinte(fornecedor, db, alvo, margem, passa):
    check = checklist_promocao(obter_fornecedor(fornecedor, db), {str(i): D(margem) for i in range(3)}, D(alvo))
    assert all(check.values()) is passa


def test_reavalia_configuracao_no_momento_da_promocao(fornecedor, produto, db):
    tres_skus(fornecedor, produto, db)
    assert all(avaliar_promocao(fornecedor, db).values())
    p = replace(obter_configuracao(db).parametros, margem_alvo_pct=D("0.30"))
    salvar_configuracao(p, 15, db)
    assert promover(fornecedor, db)
    assert obter_fornecedor(fornecedor, db)["data_oficial"] is None


def test_pausa_exige_motivo_e_bloqueia_promocao(fornecedor, produto, db):
    with pytest.raises(ValueError, match="motivo"):
        alterar_etapa(fornecedor, "Descartado ou pausado", "  ", db)
    assert obter_fornecedor(fornecedor, db)["status"] == "Descoberto"
    tres_skus(fornecedor, produto, db)
    alterar_etapa(fornecedor, "Descartado ou pausado", "Sem reposição", db)
    assert obter_fornecedor(fornecedor, db)["motivo_descarte"] == "Sem reposição"
    assert promover(fornecedor, db)
    alterar_etapa(fornecedor, "Em contato", caminho=db)
    assert promover(fornecedor, db) == []


def test_etapa_invalida():
    with pytest.raises(ValueError):
        validar_etapa("inventada")


def test_historico_contato(fornecedor, db):
    ontem = date.today() - timedelta(days=1)
    registrar_interacao(fornecedor, ontem, "WhatsApp", "Contato fictício", db)
    registrar_interacao(fornecedor, date.today(), "Telefone", "Retorno fictício", db)
    contatos = listar_interacoes(fornecedor, db)
    assert [c["canal"] for c in contatos] == ["Telefone", "WhatsApp"]
    assert contatos[1]["data"] == ontem.isoformat()


@pytest.mark.parametrize("canal,resumo", [("", "teste"), ("Telefone", "")])
def test_contato_incompleto(fornecedor, db, canal, resumo):
    with pytest.raises(ValueError):
        registrar_interacao(fornecedor, date.today(), canal, resumo, db)


def test_mesmo_produto_com_varios_fornecedores(fornecedor, produto, db):
    outro = salvar_fornecedor("Outro fictício", "", "", D(0), "", "", caminho=db)
    for f, custo in [(fornecedor, D(20)), (outro, D(25))]:
        registrar_cotacao(f, produto, "ABC", custo, 1, date.today(), D("59.90"), db)
    skus = listar_skus(produto_id=produto, caminho=db)
    assert len(skus) == 2
    p = obter_configuracao(db).parametros
    margens = {s["fornecedor_id"]: estimar_margem(s, p).contribuicao for s in skus}
    assert margens == {fornecedor: D("14.33"), outro: D("9.33")}


def test_recotacao_nao_conta_sku_duplicado_e_preserva_historico(fornecedor, produto, db):
    for custo in [D(20), D(21), D(22)]:
        registrar_cotacao(fornecedor, produto, "MESMO-CODIGO", custo, 1, date.today(), D("59.90"), db)
    skus = listar_skus(fornecedor_id=fornecedor, caminho=db)
    assert len(skus) == 1
    assert skus[0]["custo_unitario_centavos"] == 2200
    assert promover(fornecedor, db)
    with conectar(db) as c:
        assert c.execute("SELECT count(*) FROM sku_fornecedor").fetchone()[0] == 3


def test_cotacao_antiga_inserida_depois_nao_substitui_recente(fornecedor, produto, db):
    ontem = date.today() - timedelta(days=1)
    registrar_cotacao(fornecedor, produto, "ABC", D(20), 1, date.today(), D("59.90"), db)
    registrar_cotacao(fornecedor, produto, "ABC", D(10), 1, ontem, D(30), db)
    assert listar_skus(fornecedor_id=fornecedor, caminho=db)[0]["custo_unitario_centavos"] == 2000
    assert obter_fornecedor(fornecedor, db)["data_ultima_cotacao"] == date.today().isoformat()


def test_codigo_nao_pode_mudar_de_produto(fornecedor, produto, db):
    outro = salvar_produto("Outro produto fictício", "", "Candidato", caminho=db)
    registrar_cotacao(fornecedor, produto, "ABC", D(20), 1, date.today(), caminho=db)
    with pytest.raises(ValueError, match="outro produto"):
        registrar_cotacao(fornecedor, outro, "ABC", D(20), 1, date.today(), caminho=db)


def test_sku_sem_preco_nao_tem_estimativa(fornecedor, produto, db):
    registrar_cotacao(fornecedor, produto, "ABC", D(20), 1, date.today(), caminho=db)
    sku = listar_skus(caminho=db)[0]
    assert estimar_margem(sku, obter_configuracao(db).parametros) is None


@pytest.mark.parametrize("custo,qtd,preco", [(D(-1), 1, D(20)), (D(20), 0, D(20)),
    (D(20), 1.5, D(20)), (D(20), 1, D(0)), (D("20.001"), 1, D(20))])
def test_cotacao_invalida(fornecedor, produto, db, custo, qtd, preco):
    with pytest.raises(ValueError):
        registrar_cotacao(fornecedor, produto, "ABC", custo, qtd, date.today(), preco, db)
    assert listar_skus(caminho=db) == []


def test_datas_futuras_recusadas(fornecedor, produto, db):
    amanha = date.today() + timedelta(days=1)
    with pytest.raises(ValueError):
        registrar_cotacao(fornecedor, produto, "ABC", D(20), 1, amanha, caminho=db)
    with pytest.raises(ValueError):
        registrar_interacao(fornecedor, amanha, "Telefone", "Teste", db)


def test_limite_cotacao_por_data():
    hoje = date(2026, 10, 26)
    assert not cotacao_antiga("2026-10-11", 15, hoje)
    assert cotacao_antiga("2026-10-10", 15, hoje)
    assert not cotacao_antiga("2026-10-10", 30, hoje)


def test_editar_produto_preserva_id_e_verificacoes(produto, db):
    assert salvar_produto("Atualizado fictício", "Cristais", "Em avaliação", True, True, True,
                          produto_id=produto, caminho=db) == produto
    p = listar_produtos(db)[0]
    assert p["nome"] == "Atualizado fictício"
    assert p["qualidade_conferida"] == 1
