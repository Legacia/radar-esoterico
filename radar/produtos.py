"""Catálogo e histórico de cotações. Um código por fornecedor identifica o SKU."""
from datetime import date
from decimal import Decimal

from radar.banco import conectar
from radar.apoio import SQL_EMBALAGEM_PRODUTO
from radar.margem import calcular, com_embalagem
from radar.valores import centavos, data_iso, obrigatorio


def listar_produtos(caminho=None):
    with conectar(caminho) as c:
        return [dict(r) for r in c.execute("SELECT * FROM produto ORDER BY nome, id")]


def salvar_produto(nome, familia, status, especificacoes=False, procedencia=False,
                   qualidade=False, produto_id=None, caminho=None):
    nome = obrigatorio(nome, "o nome do produto")
    status = obrigatorio(status, "o status do produto")
    campos = (nome, familia.strip(), status, bool(especificacoes), bool(procedencia), bool(qualidade))
    with conectar(caminho) as c:
        if produto_id is None:
            return c.execute("""INSERT INTO produto(nome, familia, status, especificacoes_conferidas,
                procedencia_conferida, qualidade_conferida) VALUES (?, ?, ?, ?, ?, ?)""", campos).lastrowid
        cursor = c.execute("""UPDATE produto SET nome=?, familia=?, status=?, especificacoes_conferidas=?,
            procedencia_conferida=?, qualidade_conferida=? WHERE id=?""", campos + (produto_id,))
        if not cursor.rowcount:
            raise ValueError("Produto não encontrado.")
        return produto_id


def _skus_atuais(c, fornecedor_id=None, produto_id=None):
    # Não contar re-cotações do mesmo SKU como produtos adicionais para promoção.
    sql = """WITH cotacoes AS (
        SELECT s.*, ROW_NUMBER() OVER (
            PARTITION BY fornecedor_id, codigo COLLATE NOCASE ORDER BY data_cotacao DESC, id DESC) AS posicao
        FROM sku_fornecedor s)
        SELECT s.*, p.nome AS produto, f.nome AS fornecedor,
            """ + SQL_EMBALAGEM_PRODUTO.format("s.produto_id") + """ AS embalagem_centavos FROM cotacoes s
        JOIN produto p ON p.id=s.produto_id JOIN fornecedor f ON f.id=s.fornecedor_id
        WHERE s.posicao=1"""
    argumentos = []
    if fornecedor_id is not None:
        sql += " AND s.fornecedor_id=?"
        argumentos.append(fornecedor_id)
    if produto_id is not None:
        sql += " AND s.produto_id=?"
        argumentos.append(produto_id)
    return [dict(r) for r in c.execute(sql + " ORDER BY p.nome, s.codigo", argumentos)]


def listar_skus(fornecedor_id=None, produto_id=None, caminho=None):
    with conectar(caminho) as c:
        return _skus_atuais(c, fornecedor_id, produto_id)


def excluir_sku(sku_id, fornecedor_id, codigo, caminho=None):
    """Exclui um SKU de fornecedor: todas as cotações do mesmo código (sem diferenciar maiúsculas).

    Só sem histórico ligado (decisão do Legacia em 28/10/2026): se alguma cotação desse código está
    num kit, no plano de compra ou num cenário de margem, nada é apagado e a mensagem diz onde.
    O fornecedor e o código confirmados na tela precisam conferir com o registro: com duas pessoas
    usando o Radar, um identificador pode ser reaproveitado depois de uma exclusão, e uma tela antiga
    não pode apagar outro SKU. Devolve quantas cotações foram apagadas.
    """
    with conectar(caminho) as c:
        sku = c.execute("SELECT fornecedor_id, codigo FROM sku_fornecedor WHERE id=?", (sku_id,)).fetchone()
        if sku is None or sku["fornecedor_id"] != fornecedor_id or sku["codigo"].casefold() != str(codigo).casefold():
            raise ValueError("Cotação não encontrada. Ela pode ter sido alterada ou excluída por outra pessoa; recarregue a tela.")
        ids = [r[0] for r in c.execute(
            "SELECT id FROM sku_fornecedor WHERE fornecedor_id=? AND codigo=? COLLATE NOCASE", (sku["fornecedor_id"], sku["codigo"]))]
        marcas = ",".join("?" * len(ids))
        usos = [nome for tabela, nome in (("kit_item", "kits"), ("plano_compra", "plano de compra"), ("cenario_margem", "cenários de margem"))
                if c.execute(f"SELECT 1 FROM {tabela} WHERE sku_fornecedor_id IN ({marcas}) LIMIT 1", ids).fetchone()]
        if usos:
            raise ValueError(f"Não é possível excluir o SKU {sku['codigo']}: ele está em uso em {', '.join(usos)}. "
                             "Troque a cotação usada lá antes de excluir.")
        c.execute(f"DELETE FROM sku_fornecedor WHERE id IN ({marcas})", ids)
        _atualizar_ultima_cotacao(c, fornecedor_id)
        return len(ids)


def _atualizar_ultima_cotacao(c, fornecedor_id):
    # Maior data entre as cotações que restaram; nula quando o fornecedor fica sem cotações.
    c.execute("""UPDATE fornecedor SET data_ultima_cotacao=
        (SELECT MAX(data_cotacao) FROM sku_fornecedor WHERE fornecedor_id=?) WHERE id=?""",
        (fornecedor_id, fornecedor_id))


def registrar_cotacao(fornecedor_id, produto_id, codigo, custo, quantidade_minima,
                      data_cotacao, preco_venda=None, caminho=None):
    codigo = obrigatorio(codigo, "o código do SKU")
    if type(quantidade_minima) is not int or quantidade_minima < 1:
        raise ValueError("A quantidade mínima deve ser um inteiro maior que zero.")
    custo_centavos = centavos(custo)
    preco_centavos = None if preco_venda is None else centavos(preco_venda)
    if preco_centavos == 0:
        raise ValueError("O preço conservador deve ser maior que zero, ou ficar em branco.")
    data = data_iso(data_cotacao)
    if data_cotacao > date.today():
        raise ValueError("A cotação não pode ter data futura.")
    with conectar(caminho) as c:
        c.execute("BEGIN IMMEDIATE")
        if not c.execute("SELECT 1 FROM fornecedor WHERE id=?", (fornecedor_id,)).fetchone():
            raise ValueError("Fornecedor não encontrado.")
        if not c.execute("SELECT 1 FROM produto WHERE id=?", (produto_id,)).fetchone():
            raise ValueError("Produto não encontrado.")
        # "INC-1" e "inc-1" são o mesmo código; a recotação mantém a grafia já registrada.
        anterior = c.execute("""SELECT produto_id, codigo FROM sku_fornecedor
            WHERE fornecedor_id=? AND codigo=? COLLATE NOCASE ORDER BY id LIMIT 1""",
            (fornecedor_id, codigo)).fetchone()
        if anterior and anterior[0] != produto_id:
            raise ValueError("Este código já identifica outro produto neste fornecedor.")
        if anterior:
            codigo = anterior[1]
        cursor = c.execute("""INSERT INTO sku_fornecedor (fornecedor_id, produto_id, codigo,
            custo_unitario_centavos, quantidade_minima, data_cotacao, preco_venda_centavos)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (fornecedor_id, produto_id, codigo, custo_centavos, quantidade_minima, data, preco_centavos))
        _atualizar_ultima_cotacao(c, fornecedor_id)
        return cursor.lastrowid


def estimar_margem(sku, parametros):
    """Margem com o preço conservador da cotação e a embalagem do produto (itens de apoio ou padrão)."""
    if sku["preco_venda_centavos"] is None:
        return None
    return calcular(Decimal(sku["preco_venda_centavos"]) / 100,
                    Decimal(sku["custo_unitario_centavos"]) / 100,
                    com_embalagem(parametros, sku.get("embalagem_centavos")))


def cotacao_antiga(data_cotacao, limite_dias, hoje=None):
    return ((hoje or date.today()) - date.fromisoformat(data_cotacao)).days > limite_dias
