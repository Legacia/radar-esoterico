"""Indicadores, tarefas e pendências calculadas a partir das datas registradas."""
from datetime import date

from radar.banco import conectar
from radar.compras import _avaliar
from radar.fornecedores.regras import ETAPAS
from radar.margem.configuracao import _ler
from radar.produtos import _skus_atuais, cotacao_antiga, estimar_margem
from radar.valores import obrigatorio


def calcular_pendencias(fornecedores, skus, interacoes, parametros, limite_dias, hoje):
    resultado = []
    ativos = {f["id"]: f for f in fornecedores if f["status"] != "Descartado ou pausado"}
    ultimos = {}
    for contato in interacoes:
        if contato["situacao_resposta"] not in ("aguardando", "recebida"):
            continue
        anterior = ultimos.get(contato["fornecedor_id"])
        if anterior is None or (contato["data"], contato["id"]) > (anterior["data"], anterior["id"]):
            ultimos[contato["fornecedor_id"]] = contato
    for f in ativos.values():
        contato = ultimos.get(f["id"])
        if (f["status"] == "Em contato" and contato and contato["situacao_resposta"] == "aguardando"
                and (hoje - date.fromisoformat(contato["data"])).days > 5):
            resultado.append({"tipo": "Sem resposta há mais de 5 dias", "referencia": f["nome"],
                "data": contato["data"], "responsavel": "Legacia"})
        if f["status"] == "Em avaliação" and not f["amostra_avaliada"]:
            resultado.append({"tipo": "Amostra pendente", "referencia": f["nome"], "data": None, "responsavel": "Anna"})
    for sku in skus:
        if sku["fornecedor_id"] not in ativos:
            continue
        referencia = f"{sku['produto']} · {sku['fornecedor']} · {sku['codigo']}"
        if cotacao_antiga(sku["data_cotacao"], limite_dias, hoje):
            resultado.append({"tipo": "Cotação antiga", "referencia": referencia,
                "data": sku["data_cotacao"], "responsavel": "Legacia"})
        margem = estimar_margem(sku, parametros)
        if margem is not None and margem.margem_pct < parametros.margem_alvo_pct:
            resultado.append({"tipo": "Margem abaixo do alvo", "referencia": referencia,
                "data": sku["data_cotacao"], "responsavel": "Legacia"})
    return resultado


def salvar_tarefa(titulo, semana, responsavel, concluida=False, tarefa_id=None, caminho=None):
    titulo = obrigatorio(titulo, "o título da tarefa")
    responsavel = obrigatorio(responsavel, "o responsável")
    if type(semana) is not int or not 1 <= semana <= 4:
        raise ValueError("A semana deve ser um número de 1 a 4.")
    dados = titulo, semana, responsavel, bool(concluida)
    with conectar(caminho) as c:
        if tarefa_id is None:
            return c.execute("INSERT INTO tarefa(titulo,semana,responsavel,concluida) VALUES(?,?,?,?)", dados).lastrowid
        if not c.execute("UPDATE tarefa SET titulo=?,semana=?,responsavel=?,concluida=? WHERE id=?", dados + (tarefa_id,)).rowcount:
            raise ValueError("Tarefa não encontrada.")
        return tarefa_id


def obter_painel(caminho=None, hoje=None):
    with conectar(caminho) as c:
        config = _ler(c)
        fornecedores = [dict(r) for r in c.execute("SELECT * FROM fornecedor ORDER BY nome")]
        skus = _skus_atuais(c)
        contatos = [dict(r) for r in c.execute("SELECT * FROM interacao")]
        tarefas = [dict(r) for r in c.execute("SELECT * FROM tarefa ORDER BY semana,id")]
        lote = _avaliar(c)
        candidatos = c.execute("SELECT count(*) FROM produto").fetchone()[0]
    return {"fornecedores_ativos": sum(f["status"] != "Descartado ou pausado" for f in fornecedores),
        "candidatos": candidatos, "prontos": sum(i["pronto"] for i in lote["itens"]),
        "comprometido_centavos": lote["comprometido_centavos"], "tarefas": tarefas,
        "concluidas": sum(t["concluida"] for t in tarefas),
        "funil": [{"etapa": e, "quantidade": sum(f["status"] == e for f in fornecedores)} for e in ETAPAS],
        "pendencias": calcular_pendencias(fornecedores, skus, contatos, config.parametros,
                                          config.limite_cotacao_dias, hoje or date.today())}
