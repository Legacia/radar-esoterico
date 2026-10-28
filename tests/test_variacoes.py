"""Variações (SKUs internos), código RAD e conversão para a unidade de venda (decisões de 28/10/2026)."""
from datetime import date
from decimal import Decimal as D

from fastapi.testclient import TestClient
import pytest

from radar.api import criar_app
from radar.banco import conectar, inicializar
from radar.banco.esquema import MIGRACOES
from radar.fornecedores import salvar_fornecedor
from radar.margem.configuracao import obter_configuracao
from radar.produtos import (custo_por_unidade_venda, estimar_margem, excluir_variacao, listar_skus,
    listar_variacoes, registrar_cotacao, salvar_produto, salvar_variacao)

EMAIL, SENHA = "teste@example.invalid", "senha-ficticia-123"
HOJE = date.today()


@pytest.fixture
def base(db):
    f = salvar_fornecedor("Fornecedor fictício", "", "", D(0), "", "", caminho=db)
    p = salvar_produto("Incenso fictício", "Incensos", "Candidato", caminho=db)
    return {"f": f, "p": p}


def test_produto_nasce_com_uma_variacao_e_codigo_interno(db, base):
    (v,) = listar_variacoes(base["p"], db)
    assert v["codigo"] == "RAD-000001" and v["unidade_venda"] == "unidade" and v["cor"] == "" and v["tamanho"] == ""
    outro = salvar_produto("Caldeirão fictício", "", "Candidato", caminho=db)
    assert listar_variacoes(outro, db)[0]["codigo"] == "RAD-000002"


def test_codigo_interno_nunca_e_reaproveitado(db, base):
    extra = salvar_variacao(base["p"], cor="Preto", caminho=db)
    excluir_variacao(extra, "RAD-000002", db)
    nova = salvar_variacao(base["p"], cor="Branco", caminho=db)
    assert [v["codigo"] for v in listar_variacoes(base["p"], db)] == ["RAD-000001", "RAD-000003"]
    assert nova != extra


def test_cor_e_tamanho_opcionais_unidade_obrigatoria(db, base):
    v = salvar_variacao(base["p"], cor="  Preto ", tamanho=" G ", unidade_venda=" caixa com 8 varetas ", caminho=db)
    linha = [x for x in listar_variacoes(base["p"], db) if x["id"] == v][0]
    assert (linha["cor"], linha["tamanho"], linha["unidade_venda"]) == ("Preto", "G", "caixa com 8 varetas")
    with pytest.raises(ValueError, match="unidade de venda"):
        salvar_variacao(base["p"], unidade_venda="  ", caminho=db)
    with pytest.raises(ValueError, match="Variação não encontrada"):
        salvar_variacao(base["p"], cor="X", variacao_id=999, caminho=db)


def test_custo_por_unidade_de_venda_arredonda_para_cima():
    assert custo_por_unidade_venda(6000, 20) == 300   # pacote com 20 caixas a R$ 60,00
    assert custo_por_unidade_venda(1000, 3) == 334    # R$ 3,333... vira R$ 3,34 (conservador)
    assert custo_por_unidade_venda(450, 1) == 450


def test_cotacao_em_pacote_usa_o_custo_da_unidade_de_venda_na_margem(db, base):
    # Pacote com 2 unidades de venda a R$ 40,00: custo de R$ 20,00 por unidade, o caso obrigatório.
    registrar_cotacao(base["f"], base["p"], "", D("40.00"), 3, HOJE, D("59.90"), db, unidades_por_cotacao=2)
    sku = listar_skus(caminho=db)[0]
    assert sku["custo_unitario_centavos"] == 2000 and sku["preco_cotado_centavos"] == 4000
    assert sku["unidades_por_cotacao"] == 2 and sku["quantidade_minima"] == 6  # 3 pacotes = 6 unidades de venda
    assert sku["codigo"] == "RAD-000001" and sku["codigo_parceiro"] == ""
    margem = estimar_margem(sku, obter_configuracao(db).parametros)
    assert margem.contribuicao == D("14.33") and margem.margem_pct.quantize(D("0.001")) == D("0.239")


def test_unidades_por_cotacao_invalidas(db, base):
    for valor in (0, -1, 100001, True, "2"):
        with pytest.raises(ValueError, match="unidades de venda por unidade cotada"):
            registrar_cotacao(base["f"], base["p"], "", D("1"), 1, HOJE, None, db, unidades_por_cotacao=valor)


def test_com_varias_variacoes_a_cotacao_exige_a_escolha(db, base):
    salvar_variacao(base["p"], tamanho="G", caminho=db)
    with pytest.raises(ValueError, match="Escolha a variação"):
        registrar_cotacao(base["f"], base["p"], "", D("1"), 1, HOJE, None, db)
    outro = salvar_produto("Outro fictício", "", "Candidato", caminho=db)
    alheia = listar_variacoes(outro, db)[0]["id"]
    with pytest.raises(ValueError, match="não pertence a este produto"):
        registrar_cotacao(base["f"], base["p"], "", D("1"), 1, HOJE, None, db, variacao_id=alheia)


def test_cada_variacao_e_um_sku_e_codigo_do_parceiro_e_opcional(db, base):
    preto = salvar_variacao(base["p"], cor="Preto", caminho=db)
    registrar_cotacao(base["f"], base["p"], "", D("2"), 1, HOJE, None, db, variacao_id=listar_variacoes(base["p"], db)[0]["id"])
    registrar_cotacao(base["f"], base["p"], "", D("3"), 1, HOJE, None, db, variacao_id=preto)
    skus = listar_skus(caminho=db)
    assert [(s["codigo"], s["cor"], s["custo_unitario_centavos"]) for s in skus] == [
        ("RAD-000001", "", 200), ("RAD-000002", "Preto", 300)]
    # Código do parceiro vazio não colide entre variações; preenchido, identifica uma só variação.
    registrar_cotacao(base["f"], base["p"], "P-1", D("3"), 1, HOJE, None, db, variacao_id=preto)
    with pytest.raises(ValueError, match="outra variação"):
        registrar_cotacao(base["f"], base["p"], "p-1", D("3"), 1, HOJE, None, db,
                          variacao_id=listar_variacoes(base["p"], db)[0]["id"])


def test_exclusao_de_variacao(db, base):
    (v,) = listar_variacoes(base["p"], db)
    with pytest.raises(ValueError, match="pelo menos uma variação"):
        excluir_variacao(v["id"], v["codigo"], db)
    extra = salvar_variacao(base["p"], cor="Azul", caminho=db)
    registrar_cotacao(base["f"], base["p"], "", D("1"), 1, HOJE, None, db, variacao_id=extra)
    with pytest.raises(ValueError, match="há cotações"):
        excluir_variacao(extra, "RAD-000002", db)
    with pytest.raises(ValueError, match="recarregue a tela"):
        excluir_variacao(extra, "RAD-000099", db)


def test_migracao_cria_variacao_padrao_para_dados_antigos(tmp_path):
    db = tmp_path / "versao4.db"
    with conectar(db) as c:
        for migracao in MIGRACOES[:4]:
            for comando in migracao:
                c.execute(comando)
        c.execute("PRAGMA user_version=4")
        c.execute("INSERT INTO fornecedor(id,nome) VALUES(1,'Fictício')")
        c.execute("INSERT INTO produto(id,nome) VALUES(7,'Fictício A'),(9,'Fictício B')")
        c.execute("""INSERT INTO sku_fornecedor(fornecedor_id,produto_id,codigo,custo_unitario_centavos,
            quantidade_minima,data_cotacao) VALUES(1,7,'INC-1',450,10,'2026-10-01')""")
    inicializar(db)
    assert listar_variacoes(7, db)[0]["codigo"] == "RAD-000001"
    assert listar_variacoes(9, db)[0]["codigo"] == "RAD-000002"
    (sku,) = listar_skus(caminho=db)
    assert (sku["codigo"], sku["codigo_parceiro"], sku["custo_unitario_centavos"]) == ("RAD-000001", "INC-1", 450)
    assert (sku["preco_cotado_centavos"], sku["unidades_por_cotacao"], sku["quantidade_minima"]) == (450, 1, 10)
    # Depois da migração, um produto novo continua a sequência sem repetir códigos.
    novo = salvar_produto("Fictício C", "", "Candidato", caminho=db)
    assert listar_variacoes(novo, db)[0]["codigo"] == "RAD-000003"


def test_rotas_de_variacao_e_cotacao(db, conta, base):
    with TestClient(criar_app()) as cliente:
        assert cliente.post(f"/api/produtos/{base['p']}/variacoes", json={"cor": "Preto"}).status_code == 401
        cliente.post("/api/entrar", json={"email": EMAIL, "senha": SENHA})
        v = cliente.post(f"/api/produtos/{base['p']}/variacoes",
                         json={"cor": "Preto", "tamanho": "G", "unidade_venda": "caixa"}).json()["id"]
        assert cliente.put(f"/api/produtos/{base['p']}/variacoes/{v}",
                           json={"cor": "Preto fosco", "tamanho": "G", "unidade_venda": "caixa"}).status_code == 200
        r = cliente.post(f"/api/produtos/{base['p']}/cotacoes", json={
            "fornecedor_id": base["f"], "variacao_id": v, "custo": "60,00", "unidades_por_cotacao": 20,
            "quantidade_minima": 1, "data": HOJE.isoformat(), "preco_venda": "9,90"})
        assert r.status_code == 200
        ficha = cliente.get(f"/api/produtos/{base['p']}").json()
        assert [x["codigo"] for x in ficha["variacoes"]] == ["RAD-000001", "RAD-000002"]
        assert ficha["variacoes"][1]["cor"] == "Preto fosco" and ficha["variacoes"][1]["cotacoes"] == 1
        sku = ficha["skus"][0]
        assert (sku["codigo"], sku["codigo_parceiro"], sku["custo_centavos"]) == ("RAD-000002", "", 300)
        assert (sku["preco_cotado_centavos"], sku["unidades_por_cotacao"], sku["quantidade_minima"]) == (6000, 20, 20)
        assert sku["unidade_venda"] == "caixa" and sku["tamanho"] == "G"
        apagar = cliente.delete(f"/api/variacoes/{v}", params={"codigo": "RAD-000002"})
        assert apagar.status_code == 400 and "há cotações" in apagar.json()["detail"]


def test_exclusoes_simultaneas_nao_deixam_produto_sem_variacao(db, base):
    # Duas pessoas excluem, ao mesmo tempo, cada uma uma das duas variações do produto.
    import threading
    import radar.produtos as produtos
    extra = salvar_variacao(base["p"], cor="Azul", caminho=db)
    primeira = listar_variacoes(base["p"], db)[0]
    barreira, erros = threading.Barrier(2), []
    original = produtos.conectar

    def conectar_sincronizado(caminho=None):
        conexao = original(caminho)
        entrada = conexao.__enter__

        class Sincronizada:
            def __enter__(self):
                c = entrada()
                barreira.wait(timeout=5)  # as duas abrem a conexão juntas, antes de conferir
                return c

            def __exit__(self, *args):
                return conexao.__exit__(*args)
        return Sincronizada()

    produtos.conectar = conectar_sincronizado
    try:
        def excluir(vid, codigo):
            try:
                excluir_variacao(vid, codigo, db)
            except ValueError as erro:
                erros.append(str(erro))
        tarefas = [threading.Thread(target=excluir, args=a) for a in ((primeira["id"], primeira["codigo"]), (extra, "RAD-000002"))]
        for t in tarefas:
            t.start()
        for t in tarefas:
            t.join()
    finally:
        produtos.conectar = original
    assert len(listar_variacoes(base["p"], db)) == 1
    assert erros == ["O produto precisa de pelo menos uma variação."]
