"""Anúncios e preços datados; nenhuma coleta automática de marketplace."""
from datetime import date
from decimal import Decimal
from urllib.parse import urlsplit

from radar.banco import conectar
from radar.apoio import embalagem_produto
from radar.margem import calcular, com_embalagem, preco_minimo
from radar.margem.configuracao import _ler
from radar.valores import centavos, data_iso, obrigatorio


def validar_anuncio(marketplace, titulo, url, preco, data, sinal=""):
    marketplace = obrigatorio(marketplace, "o marketplace").casefold()
    titulo = obrigatorio(titulo, "o título")
    url = obrigatorio(url, "a URL")
    try:
        partes = urlsplit(url)
        valido = (partes.scheme in ("http", "https") and partes.hostname and not partes.username
                  and not partes.password and not any(c.isspace() for c in url))
        partes.port
    except ValueError:
        valido = False
    if not valido:
        raise ValueError("A URL deve usar http ou https e ter um endereço válido, sem credenciais.")
    valor = centavos(preco)
    if valor <= 0:
        raise ValueError("O preço observado deve ser maior que zero.")
    data_texto = data_iso(data)
    if data > date.today():
        raise ValueError("O preço observado não pode ter data futura.")
    return marketplace, titulo, url, valor, data_texto, sinal.strip()


def _registrar(c, dados, produto_id=None):
    marketplace, titulo, url, valor, data, sinal = dados
    if produto_id is not None and not c.execute("SELECT 1 FROM produto WHERE id=?", (produto_id,)).fetchone():
        raise ValueError("Produto não encontrado.")
    anuncio = c.execute("SELECT id, produto_id FROM anuncio WHERE marketplace=? AND url=?", (marketplace, url)).fetchone()
    if anuncio:
        anuncio_id = anuncio["id"]
        if produto_id is not None and anuncio["produto_id"] not in (None, produto_id):
            raise ValueError("Este anúncio já está ligado a outro produto; revise o vínculo na Pesquisa.")
        c.execute("""UPDATE anuncio SET titulo=?, sinal=?, produto_id=COALESCE(produto_id, ?) WHERE id=?""",
                  (titulo, sinal, produto_id, anuncio_id))
    else:
        anuncio_id = c.execute("INSERT INTO anuncio(marketplace,titulo,url,produto_id,sinal) VALUES(?,?,?,?,?)",
                               (marketplace, titulo, url, produto_id, sinal)).lastrowid
    cursor = c.execute("INSERT OR IGNORE INTO preco_observado(anuncio_id,preco_centavos,data) VALUES(?,?,?)",
                       (anuncio_id, valor, data))
    return anuncio_id, cursor.rowcount == 1


def registrar_anuncio(marketplace, titulo, url, preco, data, produto_id=None, sinal="", caminho=None):
    dados = validar_anuncio(marketplace, titulo, url, preco, data, sinal)
    with conectar(caminho) as c:
        c.execute("BEGIN IMMEDIATE")
        return _registrar(c, dados, produto_id)


def vincular_produto(anuncio_id, produto_id, caminho=None):
    with conectar(caminho) as c:
        if produto_id is not None and not c.execute("SELECT 1 FROM produto WHERE id=?", (produto_id,)).fetchone():
            raise ValueError("Produto não encontrado.")
        if not c.execute("UPDATE anuncio SET produto_id=? WHERE id=?", (produto_id, anuncio_id)).rowcount:
            raise ValueError("Anúncio não encontrado.")


def listar_anuncios(caminho=None):
    with conectar(caminho) as c:
        return [dict(r) for r in c.execute("SELECT a.*, p.nome AS produto FROM anuncio a LEFT JOIN produto p ON p.id=a.produto_id ORDER BY a.titulo,a.id")]


def listar_cotacoes(produto_id, caminho=None):
    with conectar(caminho) as c:
        return [dict(r) for r in c.execute("""SELECT s.*, f.nome AS fornecedor FROM sku_fornecedor s
            JOIN fornecedor f ON f.id=s.fornecedor_id WHERE s.produto_id=? ORDER BY s.data_cotacao DESC,s.id DESC""", (produto_id,))]


def mediana_precos(valores):
    valores = sorted(valores)
    if not valores:
        return None
    meio = len(valores) // 2
    return valores[meio] if len(valores) % 2 else (valores[meio - 1] + valores[meio]) / 2


def pesquisar(produto_id, cotacao_id, marketplace="", termo="", caminho=None):
    with conectar(caminho) as c:
        cotacao = c.execute("SELECT * FROM sku_fornecedor WHERE id=? AND produto_id=?", (cotacao_id, produto_id)).fetchone()
        if not cotacao:
            raise ValueError("Selecione uma cotação do produto pesquisado.")
        # Embalagem do produto pesquisado: itens de apoio indicados ou a padrão.
        p = com_embalagem(_ler(c).parametros, embalagem_produto(c, produto_id))
        # Cada anúncio entra uma vez nas estatísticas; o histórico aparece à parte.
        sql = """WITH precos AS (SELECT *, ROW_NUMBER() OVER (
            PARTITION BY anuncio_id ORDER BY data DESC,id DESC) AS posicao FROM preco_observado)
            SELECT a.id,a.marketplace,a.titulo,a.url,a.sinal,o.preco_centavos,o.data
            FROM anuncio a JOIN precos o ON o.anuncio_id=a.id AND o.posicao=1 WHERE a.produto_id=?"""
        args = [produto_id]
        if marketplace.strip():
            sql += " AND a.marketplace=?"
            args.append(marketplace.strip().casefold())
        linhas = [dict(r) for r in c.execute(sql + " ORDER BY o.preco_centavos,a.id", args)
                  if termo.strip().casefold() in r["titulo"].casefold()]
        custo = Decimal(cotacao["custo_unitario_centavos"]) / 100
        for linha in linhas:
            linha["preco"] = Decimal(linha["preco_centavos"]) / 100
            resultado = calcular(linha["preco"], custo, p)
            linha["contribuicao"] = resultado.contribuicao
            linha["margem"] = resultado.margem_pct
        ids = {r["id"] for r in linhas}
        historico = [dict(r) for r in c.execute("""SELECT a.id AS anuncio_id,a.titulo,o.preco_centavos,o.data
            FROM anuncio a JOIN preco_observado o ON o.anuncio_id=a.id WHERE a.produto_id=?
            ORDER BY o.data DESC,o.id DESC""", (produto_id,)) if r["anuncio_id"] in ids]
    try:
        minimo = preco_minimo(custo, p)
    except ValueError:
        minimo = None
    return {"linhas": linhas, "historico": historico, "mediana": mediana_precos([r["preco"] for r in linhas]),
            "preco_minimo": minimo, "no_alvo": sum(r["margem"] >= p.margem_alvo_pct for r in linhas),
            "custo": custo, "data_cotacao": cotacao["data_cotacao"], "embalagem": p.embalagem}
