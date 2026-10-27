"""CSV UTF-8, separado por ponto e vírgula, com relatório por linha física."""
import csv
from dataclasses import dataclass, field
from datetime import date
import io

from radar.banco import conectar
from radar.mercado import _registrar, validar_anuncio
from radar.valores import dinheiro_texto

COLUNAS = ("marketplace", "titulo", "url", "preco", "data")


@dataclass
class RelatorioImportacao:
    importadas: int = 0
    repetidas: int = 0
    erros: list = field(default_factory=list)


def importar_csv(conteudo, caminho=None):
    if isinstance(conteudo, bytes):
        try:
            conteudo = conteudo.decode("utf-8-sig")
        except UnicodeDecodeError as erro:
            raise ValueError("Salve o CSV com codificação UTF-8.") from erro
    if not isinstance(conteudo, str):
        raise ValueError("Informe o conteúdo de um CSV UTF-8.")
    leitor = csv.DictReader(io.StringIO(conteudo.lstrip("\ufeff")), delimiter=";", strict=True)
    try:
        cabecalho = leitor.fieldnames
    except csv.Error as erro:
        raise ValueError("Cabeçalho CSV inválido.") from erro
    if not cabecalho or len(cabecalho) != len(set(cabecalho)) or not set(COLUNAS).issubset(cabecalho):
        raise ValueError("Cabeçalho obrigatório: marketplace;titulo;url;preco;data. Opcionais: produto;sinal.")
    if set(cabecalho) - set(COLUNAS) - {"produto", "sinal"}:
        raise ValueError("O CSV contém colunas não reconhecidas. Use o formato do exemplo.")
    relatorio = RelatorioImportacao()
    with conectar(caminho) as c:
        c.execute("BEGIN IMMEDIATE")
        produtos = {}
        for p in c.execute("SELECT id,nome FROM produto"):
            produtos.setdefault(p["nome"].strip().casefold(), []).append(p["id"])
        while True:
            linha = leitor.reader.line_num + 1
            try:
                campos = next(leitor.reader)
            except StopIteration:
                break
            except csv.Error:
                relatorio.erros.append({"linha": linha, "erro": "Estrutura CSV inválida; revise aspas e separadores."})
                continue
            if not campos:
                continue
            c.execute("SAVEPOINT linha_csv")
            try:
                if len(campos) != len(cabecalho):
                    raise ValueError("Quantidade de campos diferente do cabeçalho.")
                registro = dict(zip(cabecalho, campos))
                data_texto = registro["data"].strip()
                try:
                    data = date.fromisoformat(data_texto)
                except ValueError as erro:
                    raise ValueError("Data inválida. Use AAAA-MM-DD.") from erro
                if data.isoformat() != data_texto:
                    raise ValueError("Use a data no formato AAAA-MM-DD.")
                dados = validar_anuncio(registro["marketplace"], registro["titulo"], registro["url"],
                    dinheiro_texto(registro["preco"]), data, registro.get("sinal", ""))
                nome = registro.get("produto", "").strip().casefold()
                correspondencias = produtos.get(nome, [])
                if nome and len(correspondencias) != 1:
                    raise ValueError("Produto não encontrado ou nome ambíguo. Cadastre-o ou deixe a coluna produto em branco.")
                _, novo = _registrar(c, dados, correspondencias[0] if nome else None)
                if novo:
                    relatorio.importadas += 1
                else:
                    relatorio.repetidas += 1
            except ValueError as erro:
                c.execute("ROLLBACK TO linha_csv")
                relatorio.erros.append({"linha": linha, "erro": str(erro)})
            finally:
                c.execute("RELEASE linha_csv")
    return relatorio
