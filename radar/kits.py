"""Composição, custo por cotação e necessidade de estoque por componente."""
from decimal import Decimal

from radar.banco import conectar
from radar.valores import obrigatorio


def listar_kits(caminho=None):
    with conectar(caminho) as c:
        return [dict(r) for r in c.execute("SELECT * FROM kit ORDER BY nome,id")]


def salvar_kit(nome, kit_id=None, caminho=None):
    nome = obrigatorio(nome, "o nome do kit")
    with conectar(caminho) as c:
        if kit_id is None:
            return c.execute("INSERT INTO kit(nome) VALUES(?)", (nome,)).lastrowid
        if not c.execute("UPDATE kit SET nome=? WHERE id=?", (nome, kit_id)).rowcount:
            raise ValueError("Kit não encontrado.")
        return kit_id


def salvar_componente(kit_id, produto_id, quantidade, cotacao_id, caminho=None):
    if type(quantidade) is not int or not 1 <= quantidade <= 9223372036854775807:
        raise ValueError("A quantidade do componente deve ser um inteiro positivo.")
    with conectar(caminho) as c:
        if not c.execute("SELECT 1 FROM kit WHERE id=?", (kit_id,)).fetchone():
            raise ValueError("Kit não encontrado.")
        if not c.execute("SELECT 1 FROM sku_fornecedor WHERE id=? AND produto_id=?", (cotacao_id, produto_id)).fetchone():
            raise ValueError("Escolha uma cotação do componente selecionado.")
        c.execute("""INSERT INTO kit_item(kit_id,produto_id,quantidade,sku_fornecedor_id) VALUES(?,?,?,?)
            ON CONFLICT(kit_id,produto_id) DO UPDATE SET quantidade=excluded.quantidade,
            sku_fornecedor_id=excluded.sku_fornecedor_id""", (kit_id,produto_id,quantidade,cotacao_id))


def remover_componente(kit_id, produto_id, caminho=None):
    with conectar(caminho) as c:
        c.execute("DELETE FROM kit_item WHERE kit_id=? AND produto_id=?", (kit_id,produto_id))


def ajustar_estoque(produto_id, quantidade, caminho=None):
    if type(quantidade) is not int or not 0 <= quantidade <= 9223372036854775807:
        raise ValueError("O estoque deve ser um inteiro não negativo dentro do limite do banco.")
    with conectar(caminho) as c:
        if not c.execute("UPDATE produto SET estoque_atual=? WHERE id=?", (quantidade,produto_id)).rowcount:
            raise ValueError("Produto não encontrado.")


def planejar_kits(kit_id, quantidade, caminho=None):
    if type(quantidade) is not int or not 0 <= quantidade <= 9223372036854775807:
        raise ValueError("A quantidade planejada deve ser um inteiro não negativo.")
    with conectar(caminho) as c:
        if not c.execute("UPDATE kit SET quantidade_planejada=? WHERE id=?", (quantidade,kit_id)).rowcount:
            raise ValueError("Kit não encontrado.")


def necessidade_conjunta(caminho=None):
    with conectar(caminho) as c:
        itens = c.execute("""SELECT p.id,p.nome,p.estoque_atual,ki.quantidade,k.quantidade_planejada
            FROM kit_item ki JOIN kit k ON k.id=ki.kit_id JOIN produto p ON p.id=ki.produto_id
            WHERE k.quantidade_planejada > 0""").fetchall()
    por_produto = {}
    for item in itens:
        linha = por_produto.setdefault(item["id"], {"produto": item["nome"], "estoque": item["estoque_atual"], "necessario": 0})
        linha["necessario"] += item["quantidade"] * item["quantidade_planejada"]
    return [dict(linha, falta=max(0,linha["necessario"]-linha["estoque"])) for linha in por_produto.values()]


def calcular_necessidades(componentes, quantidade_kits):
    if type(quantidade_kits) is not int or quantidade_kits < 1:
        raise ValueError("Informe uma quantidade inteira positiva de kits.")
    linhas, total = [], 0
    completo = bool(componentes)
    for item in componentes:
        linha = dict(item)
        linha["necessario"] = item["quantidade"] * quantidade_kits
        linha["falta"] = max(0, linha["necessario"] - item["estoque_atual"])
        custo = item["custo_unitario_centavos"]
        if custo is None:
            completo = False
        else:
            total += custo * item["quantidade"]
        linhas.append(linha)
    if total * quantidade_kits > 9223372036854775807:
        raise ValueError("O custo planejado está fora do limite monetário do banco.")
    return {"componentes": linhas, "custo_unitario": Decimal(total) / 100 if completo else None,
            "custo_lote": Decimal(total * quantidade_kits) / 100 if completo else None}


def consultar_kit(kit_id, quantidade_kits=1, caminho=None):
    with conectar(caminho) as c:
        if not c.execute("SELECT 1 FROM kit WHERE id=?", (kit_id,)).fetchone():
            raise ValueError("Kit não encontrado.")
        componentes = [dict(r) for r in c.execute("""SELECT ki.*,p.nome AS produto,p.estoque_atual,
            s.custo_unitario_centavos,s.data_cotacao,s.codigo FROM kit_item ki
            JOIN produto p ON p.id=ki.produto_id LEFT JOIN sku_fornecedor s ON s.id=ki.sku_fornecedor_id
            WHERE ki.kit_id=? ORDER BY p.nome""", (kit_id,))]
    return calcular_necessidades(componentes, quantidade_kits)
