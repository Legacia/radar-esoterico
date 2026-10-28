"""Itens de apoio: embalagens, caixas, sacolas e outros materiais de envio, com custo e fornecedor.

Cada produto e cada kit indica os seus itens (decisão do Legacia em 28/10/2026). A soma do custo
desses itens substitui a embalagem padrão da configuração no cálculo de margem; sem itens indicados,
vale a embalagem padrão. Um kit usa só os itens dele, não os dos componentes, porque pode precisar
de uma embalagem maior.
"""
from datetime import date

from radar.banco import conectar
from radar.valores import centavos, data_iso, obrigatorio

DESTINOS = {"produto": ("produto_apoio", "produto_id", "produto", "Produto não encontrado."),
            "kit": ("kit_apoio", "kit_id", "kit", "Kit não encontrado.")}

# Soma dos itens indicados; nula quando não há nenhum (aí vale a embalagem padrão).
SQL_EMBALAGEM_PRODUTO = """(SELECT SUM(pa.quantidade * ia.custo_centavos) FROM produto_apoio pa
    JOIN item_apoio ia ON ia.id=pa.item_apoio_id WHERE pa.produto_id={})"""


def listar_itens(caminho=None):
    with conectar(caminho) as c:
        return [dict(r) for r in c.execute("""SELECT ia.*, f.nome AS fornecedor,
            (SELECT COUNT(*) FROM produto_apoio WHERE item_apoio_id=ia.id) AS produtos,
            (SELECT COUNT(*) FROM kit_apoio WHERE item_apoio_id=ia.id) AS kits
            FROM item_apoio ia LEFT JOIN fornecedor f ON f.id=ia.fornecedor_id ORDER BY ia.nome, ia.id""")]


def salvar_item(nome, fornecedor_id, custo, data_cotacao, item_id=None, caminho=None):
    nome = obrigatorio(nome, "o nome do item")
    custo_centavos = centavos(custo)
    data = data_iso(data_cotacao)
    if data_cotacao > date.today():
        raise ValueError("A cotação não pode ter data futura.")
    with conectar(caminho) as c:
        if fornecedor_id is not None and not c.execute("SELECT 1 FROM fornecedor WHERE id=?", (fornecedor_id,)).fetchone():
            raise ValueError("Fornecedor não encontrado.")
        dados = (nome, fornecedor_id, custo_centavos, data)
        if item_id is None:
            return c.execute("INSERT INTO item_apoio(nome, fornecedor_id, custo_centavos, data_cotacao) VALUES (?, ?, ?, ?)",
                             dados).lastrowid
        if not c.execute("UPDATE item_apoio SET nome=?, fornecedor_id=?, custo_centavos=?, data_cotacao=? WHERE id=?",
                         dados + (item_id,)).rowcount:
            raise ValueError("Item de apoio não encontrado.")
        return item_id


def excluir_item(item_id, nome, caminho=None):
    """Exclui só item que não está indicado em nenhum produto ou kit.

    O nome confirmado precisa conferir, para uma tela antiga não apagar outro item com o mesmo id.
    """
    with conectar(caminho) as c:
        item = c.execute("SELECT nome FROM item_apoio WHERE id=?", (item_id,)).fetchone()
        if item is None or item["nome"] != nome:
            raise ValueError("Item não encontrado. Ele pode ter sido alterado ou excluído por outra pessoa; recarregue a tela.")
        usos = [texto for tabela, texto in (("produto_apoio", "produtos"), ("kit_apoio", "kits"))
                if c.execute(f"SELECT 1 FROM {tabela} WHERE item_apoio_id=? LIMIT 1", (item_id,)).fetchone()]
        if usos:
            raise ValueError(f"Não é possível excluir: o item está indicado em {' e '.join(usos)}. Retire-o de lá antes.")
        c.execute("DELETE FROM item_apoio WHERE id=?", (item_id,))


def _destino(tipo):
    if tipo not in DESTINOS:
        raise ValueError("Destino inválido.")
    return DESTINOS[tipo]


def indicar(tipo, destino_id, item_id, quantidade, caminho=None):
    """Indica (ou altera a quantidade de) um item de apoio usado por unidade vendida do produto ou kit."""
    tabela, coluna, origem, nao_encontrado = _destino(tipo)
    if type(quantidade) is not int or not 1 <= quantidade <= 1000:
        raise ValueError("A quantidade do item deve ser um inteiro de 1 a 1000.")
    with conectar(caminho) as c:
        if not c.execute(f"SELECT 1 FROM {origem} WHERE id=?", (destino_id,)).fetchone():
            raise ValueError(nao_encontrado)
        if not c.execute("SELECT 1 FROM item_apoio WHERE id=?", (item_id,)).fetchone():
            raise ValueError("Item de apoio não encontrado.")
        c.execute(f"""INSERT INTO {tabela}({coluna}, item_apoio_id, quantidade) VALUES (?, ?, ?)
            ON CONFLICT({coluna}, item_apoio_id) DO UPDATE SET quantidade=excluded.quantidade""",
                  (destino_id, item_id, quantidade))


def retirar(tipo, destino_id, item_id, caminho=None):
    tabela, coluna, _, _ = _destino(tipo)
    with conectar(caminho) as c:
        c.execute(f"DELETE FROM {tabela} WHERE {coluna}=? AND item_apoio_id=?", (destino_id, item_id))


def _itens_de(c, tipo, destino_id):
    tabela, coluna, _, _ = _destino(tipo)
    return [dict(r) for r in c.execute(f"""SELECT ia.id, ia.nome, ia.custo_centavos, ia.data_cotacao,
        f.nome AS fornecedor, x.quantidade, x.quantidade * ia.custo_centavos AS subtotal_centavos
        FROM {tabela} x JOIN item_apoio ia ON ia.id=x.item_apoio_id
        LEFT JOIN fornecedor f ON f.id=ia.fornecedor_id WHERE x.{coluna}=? ORDER BY ia.nome, ia.id""", (destino_id,))]


def itens_de(tipo, destino_id, caminho=None):
    """Itens indicados e a embalagem resultante em centavos (None quando vale a padrão)."""
    with conectar(caminho) as c:
        itens = _itens_de(c, tipo, destino_id)
    return {"itens": itens, "embalagem_centavos": sum(i["subtotal_centavos"] for i in itens) if itens else None}


def embalagem_produto(c, produto_id):
    return c.execute("SELECT " + SQL_EMBALAGEM_PRODUTO.format("?"), (produto_id,)).fetchone()[0]


def embalagem_kit(c, kit_id):
    return c.execute("""SELECT SUM(ka.quantidade * ia.custo_centavos) FROM kit_apoio ka
        JOIN item_apoio ia ON ia.id=ka.item_apoio_id WHERE ka.kit_id=?""", (kit_id,)).fetchone()[0]
