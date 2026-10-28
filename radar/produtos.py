"""Catálogo, variações e histórico de cotações.

O SKU é a variação do produto (decisão do Legacia em 28/10/2026): código interno RAD-000001, gerado
pelo Radar e nunca reaproveitado, com cor, tamanho e unidade de venda. Cada cotação aponta para uma
variação; o código do parceiro é opcional. O custo usado nas contas é sempre o custo por unidade de
venda: preço cotado dividido pelas unidades de venda que vêm na unidade cotada.
"""
from datetime import date
from decimal import Decimal

from radar.apoio import SQL_EMBALAGEM_PRODUTO
from radar.banco import conectar
from radar.margem import calcular, com_embalagem
from radar.valores import centavos, data_iso, obrigatorio

LIMITE_BANCO = 9223372036854775807


def listar_produtos(caminho=None):
    with conectar(caminho) as c:
        return [dict(r) for r in c.execute("SELECT * FROM produto ORDER BY nome, id")]


def _criar_variacao(c, produto_id, cor="", tamanho="", unidade_venda="unidade"):
    # AUTOINCREMENT garante que um id (e o código RAD que vem dele) nunca volta depois de uma exclusão.
    variacao_id = c.execute("INSERT INTO variacao(produto_id, cor, tamanho, unidade_venda) VALUES (?, ?, ?, ?)",
                            (produto_id, cor, tamanho, unidade_venda)).lastrowid
    c.execute("UPDATE variacao SET codigo=? WHERE id=?", (f"RAD-{variacao_id:06d}", variacao_id))
    return variacao_id


def salvar_produto(nome, familia, status, especificacoes=False, procedencia=False,
                   qualidade=False, produto_id=None, caminho=None):
    nome = obrigatorio(nome, "o nome do produto")
    status = obrigatorio(status, "o status do produto")
    campos = (nome, familia.strip(), status, bool(especificacoes), bool(procedencia), bool(qualidade))
    with conectar(caminho) as c:
        if produto_id is None:
            novo = c.execute("""INSERT INTO produto(nome, familia, status, especificacoes_conferidas,
                procedencia_conferida, qualidade_conferida) VALUES (?, ?, ?, ?, ?, ?)""", campos).lastrowid
            # Todo produto nasce com uma variação, para já poder receber cotações.
            _criar_variacao(c, novo)
            return novo
        cursor = c.execute("""UPDATE produto SET nome=?, familia=?, status=?, especificacoes_conferidas=?,
            procedencia_conferida=?, qualidade_conferida=? WHERE id=?""", campos + (produto_id,))
        if not cursor.rowcount:
            raise ValueError("Produto não encontrado.")
        return produto_id


def _texto_opcional(valor, nome):
    if not isinstance(valor, str):
        raise ValueError(f"Informe {nome} como texto.")
    return valor.strip()


def salvar_variacao(produto_id, cor="", tamanho="", unidade_venda="unidade", variacao_id=None, caminho=None):
    """Cria ou altera uma variação. Cor e tamanho são opcionais; a unidade de venda é obrigatória."""
    cor, tamanho = _texto_opcional(cor, "a cor"), _texto_opcional(tamanho, "o tamanho")
    unidade_venda = obrigatorio(unidade_venda, "a unidade de venda (por exemplo, unidade ou caixa)")
    with conectar(caminho) as c:
        if not c.execute("SELECT 1 FROM produto WHERE id=?", (produto_id,)).fetchone():
            raise ValueError("Produto não encontrado.")
        if variacao_id is None:
            return _criar_variacao(c, produto_id, cor, tamanho, unidade_venda)
        if not c.execute("UPDATE variacao SET cor=?, tamanho=?, unidade_venda=? WHERE id=? AND produto_id=?",
                         (cor, tamanho, unidade_venda, variacao_id, produto_id)).rowcount:
            raise ValueError("Variação não encontrada neste produto.")
        return variacao_id


def listar_variacoes(produto_id, caminho=None):
    with conectar(caminho) as c:
        return [dict(r) for r in c.execute("""SELECT v.*, (SELECT COUNT(*) FROM sku_fornecedor s
            WHERE s.variacao_id=v.id) AS cotacoes FROM variacao v WHERE v.produto_id=? ORDER BY v.id""", (produto_id,))]


def excluir_variacao(variacao_id, codigo, caminho=None):
    """Exclui variação sem cotações. O código confirmado precisa conferir; o produto fica com pelo menos uma."""
    with conectar(caminho) as c:
        # Conferência e exclusão na mesma transação de escrita: duas pessoas excluindo ao mesmo tempo
        # não deixam o produto sem variação, porque a segunda espera e vê a contagem já atualizada.
        c.execute("BEGIN IMMEDIATE")
        v = c.execute("SELECT produto_id, codigo FROM variacao WHERE id=?", (variacao_id,)).fetchone()
        if v is None or v["codigo"] != codigo:
            raise ValueError("Variação não encontrada. Ela pode ter sido excluída por outra pessoa; recarregue a tela.")
        if c.execute("SELECT 1 FROM sku_fornecedor WHERE variacao_id=? LIMIT 1", (variacao_id,)).fetchone():
            raise ValueError(f"Não é possível excluir {codigo}: há cotações dessa variação. Exclua o SKU nas cotações antes.")
        if c.execute("SELECT COUNT(*) FROM variacao WHERE produto_id=?", (v["produto_id"],)).fetchone()[0] == 1:
            raise ValueError("O produto precisa de pelo menos uma variação.")
        c.execute("DELETE FROM variacao WHERE id=?", (variacao_id,))


def _skus_atuais(c, fornecedor_id=None, produto_id=None):
    # Vale a cotação mais recente de cada variação por fornecedor; recotações não contam como
    # produtos adicionais para a promoção. "codigo" é o código interno (RAD); o do parceiro vem à parte.
    sql = """WITH cotacoes AS (
        SELECT s.*, ROW_NUMBER() OVER (
            PARTITION BY fornecedor_id, variacao_id ORDER BY data_cotacao DESC, id DESC) AS posicao
        FROM sku_fornecedor s)
        SELECT s.*, v.codigo AS codigo_interno, v.cor, v.tamanho, v.unidade_venda,
            p.nome AS produto, f.nome AS fornecedor,
            """ + SQL_EMBALAGEM_PRODUTO.format("s.produto_id") + """ AS embalagem_centavos FROM cotacoes s
        JOIN variacao v ON v.id=s.variacao_id
        JOIN produto p ON p.id=s.produto_id JOIN fornecedor f ON f.id=s.fornecedor_id
        WHERE s.posicao=1"""
    argumentos = []
    if fornecedor_id is not None:
        sql += " AND s.fornecedor_id=?"
        argumentos.append(fornecedor_id)
    if produto_id is not None:
        sql += " AND s.produto_id=?"
        argumentos.append(produto_id)
    return [com_codigo_interno(r) for r in c.execute(sql + " ORDER BY p.nome, v.codigo, f.nome", argumentos)]


def com_codigo_interno(linha):
    """Na cotação, "codigo" passa a ser o código interno (RAD) e o do parceiro fica em "codigo_parceiro"."""
    d = dict(linha)
    d["codigo_parceiro"] = d["codigo"]
    d["codigo"] = d.pop("codigo_interno")
    return d


def listar_skus(fornecedor_id=None, produto_id=None, caminho=None):
    with conectar(caminho) as c:
        return _skus_atuais(c, fornecedor_id, produto_id)


def excluir_sku(sku_id, fornecedor_id, codigo, caminho=None):
    """Exclui as cotações de uma variação (SKU) num fornecedor.

    Só sem histórico ligado (decisão do Legacia em 28/10/2026): se alguma dessas cotações está num
    kit, no plano de compra ou num cenário de margem, nada é apagado e a mensagem diz onde.
    O fornecedor e o código interno confirmados na tela precisam conferir com o registro, para uma
    tela antiga não apagar outro SKU. Devolve quantas cotações foram apagadas.
    """
    with conectar(caminho) as c:
        c.execute("BEGIN IMMEDIATE")  # conferência de uso e exclusão sem outra gravação no meio
        sku = c.execute("""SELECT s.fornecedor_id, s.variacao_id, v.codigo FROM sku_fornecedor s
            JOIN variacao v ON v.id=s.variacao_id WHERE s.id=?""", (sku_id,)).fetchone()
        if sku is None or sku["fornecedor_id"] != fornecedor_id or sku["codigo"] != str(codigo):
            raise ValueError("Cotação não encontrada. Ela pode ter sido alterada ou excluída por outra pessoa; recarregue a tela.")
        ids = [r[0] for r in c.execute(
            "SELECT id FROM sku_fornecedor WHERE fornecedor_id=? AND variacao_id=?", (fornecedor_id, sku["variacao_id"]))]
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


def custo_por_unidade_venda(preco_cotado_centavos, unidades_por_cotacao):
    """Preço da unidade cotada dividido pelas unidades de venda que vêm nela, arredondado para cima
    no centavo (cenário conservador: o custo nunca sai menor que o real)."""
    return -(-preco_cotado_centavos // unidades_por_cotacao)


def registrar_cotacao(fornecedor_id, produto_id, codigo, custo, quantidade_minima,
                      data_cotacao, preco_venda=None, caminho=None, variacao_id=None, unidades_por_cotacao=1):
    """Registra a cotação de uma variação.

    `codigo` é o código do parceiro (opcional, texto vazio quando não há). `custo` é o preço cotado e
    `quantidade_minima` o pedido mínimo, ambos na unidade cotada; `unidades_por_cotacao` diz quantas
    unidades de venda vêm nela (ex.: pacote com 20 caixas). `preco_venda` é por unidade de venda.
    Sem `variacao_id`, usa a variação do produto quando ele tem uma só.
    """
    if not isinstance(codigo, str):
        raise ValueError("Informe o código do parceiro como texto.")
    codigo = codigo.strip()
    if type(quantidade_minima) is not int or quantidade_minima < 1:
        raise ValueError("A quantidade mínima deve ser um inteiro maior que zero.")
    if type(unidades_por_cotacao) is not int or not 1 <= unidades_por_cotacao <= 100000:
        raise ValueError("As unidades de venda por unidade cotada devem ser um inteiro de 1 a 100000.")
    preco_cotado = centavos(custo)
    custo_centavos = custo_por_unidade_venda(preco_cotado, unidades_por_cotacao)
    if quantidade_minima * unidades_por_cotacao > LIMITE_BANCO:
        raise ValueError("Quantidade mínima fora do limite do banco.")
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
        if variacao_id is None:
            variacoes = [r[0] for r in c.execute("SELECT id FROM variacao WHERE produto_id=?", (produto_id,))]
            if len(variacoes) != 1:
                raise ValueError("Escolha a variação (SKU) desta cotação.")
            variacao_id = variacoes[0]
        elif not c.execute("SELECT 1 FROM variacao WHERE id=? AND produto_id=?", (variacao_id, produto_id)).fetchone():
            raise ValueError("A variação escolhida não pertence a este produto.")
        if codigo:
            # "INC-1" e "inc-1" são o mesmo código do parceiro; ele identifica uma só variação no fornecedor.
            anterior = c.execute("""SELECT variacao_id, codigo FROM sku_fornecedor
                WHERE fornecedor_id=? AND codigo=? COLLATE NOCASE ORDER BY id LIMIT 1""",
                (fornecedor_id, codigo)).fetchone()
            if anterior and anterior[0] != variacao_id:
                raise ValueError("Este código do parceiro já identifica outra variação neste fornecedor.")
            if anterior:
                codigo = anterior[1]
        cursor = c.execute("""INSERT INTO sku_fornecedor (fornecedor_id, produto_id, variacao_id, codigo,
            custo_unitario_centavos, preco_cotado_centavos, unidades_por_cotacao, quantidade_minima,
            data_cotacao, preco_venda_centavos) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (fornecedor_id, produto_id, variacao_id, codigo, custo_centavos, preco_cotado, unidades_por_cotacao,
             quantidade_minima * unidades_por_cotacao, data, preco_centavos))
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
