"""Persistência e ações explícitas de acompanhamento dos fornecedores."""
from datetime import date

from radar.banco import conectar
from radar.fornecedores.regras import ETAPAS, checklist_promocao, validar_etapa
from radar.margem.configuracao import _ler
from radar.produtos import _skus_atuais, estimar_margem
from radar.valores import centavos, data_iso, obrigatorio


def listar_fornecedores(caminho=None):
    with conectar(caminho) as c:
        return [dict(r) for r in c.execute("SELECT * FROM fornecedor ORDER BY nome, id")]


def _obter(c, fornecedor_id):
    linha = c.execute("SELECT * FROM fornecedor WHERE id=?", (fornecedor_id,)).fetchone()
    if linha is None:
        raise ValueError("Fornecedor não encontrado.")
    return dict(linha)


def obter_fornecedor(fornecedor_id, caminho=None):
    with conectar(caminho) as c:
        return _obter(c, fornecedor_id)


def salvar_fornecedor(nome, cnpj, contato, pedido_minimo, prazo, pagamento,
                       cnpj_verificado=False, condicoes_verificadas=False, emite_nota=False,
                       amostra_avaliada=False, reposicao_confirmada=False,
                       fornecedor_id=None, caminho=None):
    nome = obrigatorio(nome, "o nome do fornecedor")
    if cnpj_verificado and not cnpj.strip():
        raise ValueError("Informe o CNPJ antes de marcá-lo como verificado.")
    if condicoes_verificadas and (not prazo.strip() or not pagamento.strip()):
        raise ValueError("Informe prazo e pagamento antes de confirmar as condições.")
    dados = (nome, cnpj.strip(), contato.strip(), centavos(pedido_minimo), prazo.strip(), pagamento.strip(),
             bool(cnpj_verificado), bool(condicoes_verificadas), bool(emite_nota),
             bool(amostra_avaliada), bool(reposicao_confirmada))
    with conectar(caminho) as c:
        if fornecedor_id is None:
            return c.execute("""INSERT INTO fornecedor (nome, cnpj, contato, pedido_minimo_centavos,
                prazo, condicao_pagamento, cnpj_verificado, condicoes_verificadas, emite_nota,
                amostra_avaliada, reposicao_confirmada) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", dados).lastrowid
        cursor = c.execute("""UPDATE fornecedor SET nome=?, cnpj=?, contato=?, pedido_minimo_centavos=?,
            prazo=?, condicao_pagamento=?, cnpj_verificado=?, condicoes_verificadas=?, emite_nota=?,
            amostra_avaliada=?, reposicao_confirmada=? WHERE id=?""", dados + (fornecedor_id,))
        if not cursor.rowcount:
            raise ValueError("Fornecedor não encontrado.")
        return fornecedor_id


def excluir_fornecedor(fornecedor_id, nome, caminho=None):
    """Exclui de vez só fornecedor sem histórico (decisão do Legacia em 28/10/2026).

    Com cotações ou contatos registrados, explica o que impede; para tirá-lo da lista de trabalho
    existe a etapa "Descartado ou pausado", que preserva o histórico. O nome confirmado na tela
    precisa conferir: um identificador pode ser reaproveitado depois de uma exclusão, e uma ficha
    antiga, aberta em outro computador, não pode apagar outro fornecedor.
    """
    with conectar(caminho) as c:
        if _obter(c, fornecedor_id)["nome"] != nome:
            raise ValueError("Este fornecedor foi alterado por outra pessoa. Recarregue a ficha antes de excluir.")
        cotacoes = c.execute("SELECT COUNT(*) FROM sku_fornecedor WHERE fornecedor_id=?", (fornecedor_id,)).fetchone()[0]
        contatos = c.execute("SELECT COUNT(*) FROM interacao WHERE fornecedor_id=?", (fornecedor_id,)).fetchone()[0]
        apoio = c.execute("SELECT COUNT(*) FROM item_apoio WHERE fornecedor_id=?", (fornecedor_id,)).fetchone()[0]
        motivos = [texto for n, texto in ((cotacoes, f"{cotacoes} cotação(ões)"), (contatos, f"{contatos} contato(s)"),
                                          (apoio, f"{apoio} item(ns) de apoio")) if n]
        if motivos:
            raise ValueError(f"Não é possível excluir: o fornecedor tem {' e '.join(motivos)} registrados. "
                             "Exclua as cotações sem uso ou mova o fornecedor para \"Descartado ou pausado\".")
        c.execute("DELETE FROM fornecedor WHERE id=?", (fornecedor_id,))


def alterar_etapa(fornecedor_id, etapa, motivo="", caminho=None):
    validar_etapa(etapa, motivo)
    if etapa == "Fornecedor oficial":
        raise ValueError("Use a ação de promoção para verificar o checklist.")
    with conectar(caminho) as c:
        _obter(c, fornecedor_id)
        c.execute("UPDATE fornecedor SET status=?, motivo_descarte=CASE WHEN ?<>'' THEN ? ELSE motivo_descarte END WHERE id=?",
                  (etapa, motivo.strip(), motivo.strip(), fornecedor_id))


def registrar_interacao(fornecedor_id, data, canal, resumo, caminho=None, situacao_resposta=None):
    canal = obrigatorio(canal, "o canal de contato")
    resumo = obrigatorio(resumo, "o resumo do contato")
    if situacao_resposta not in (None, "aguardando", "recebida"):
        raise ValueError("Situação da resposta inválida.")
    data_texto = data_iso(data)
    if data > date.today():
        raise ValueError("O contato não pode ter data futura.")
    with conectar(caminho) as c:
        _obter(c, fornecedor_id)
        return c.execute("INSERT INTO interacao(fornecedor_id, data, canal, resumo, situacao_resposta) VALUES (?, ?, ?, ?, ?)",
                         (fornecedor_id, data_texto, canal, resumo, situacao_resposta)).lastrowid


def listar_interacoes(fornecedor_id, caminho=None):
    with conectar(caminho) as c:
        return [dict(r) for r in c.execute("SELECT * FROM interacao WHERE fornecedor_id=? ORDER BY data DESC, id DESC", (fornecedor_id,))]


def _checklist(c, fornecedor_id):
    config = _ler(c)
    # Cada produto conta uma vez, pela melhor margem entre os seus códigos atuais.
    margens = {}
    for sku in _skus_atuais(c, fornecedor_id):
        resultado = estimar_margem(sku, config.parametros)
        atual = margens.setdefault(sku["produto_id"], None)
        if resultado and (atual is None or resultado.margem_pct > atual):
            margens[sku["produto_id"]] = resultado.margem_pct
    return checklist_promocao(_obter(c, fornecedor_id), margens, config.parametros.margem_alvo_pct)


def avaliar_promocao(fornecedor_id, caminho=None):
    with conectar(caminho) as c:
        return _checklist(c, fornecedor_id)


def promover(fornecedor_id, caminho=None):
    with conectar(caminho) as c:
        # Recalcular dentro da mesma transação impede promover com dados já alterados.
        c.execute("BEGIN IMMEDIATE")
        pendencias = [nome for nome, ok in _checklist(c, fornecedor_id).items() if not ok]
        if pendencias:
            return pendencias
        c.execute("""UPDATE fornecedor SET status='Fornecedor oficial',
            data_oficial=COALESCE(data_oficial, ?) WHERE id=?""", (date.today().isoformat(), fornecedor_id))
        return []
