"""Valores monetários em centavos inteiros; percentuais em texto decimal.

Migrações publicadas não devem ser alteradas: acrescente uma nova tupla.
As regras comerciais dos blocos seguintes serão aplicadas em radar/.
"""

MIGRACOES = ((
    """CREATE TABLE usuario (
        id INTEGER PRIMARY KEY,
        nome TEXT NOT NULL CHECK(length(trim(nome)) > 0),
        email TEXT NOT NULL UNIQUE COLLATE NOCASE,
        senha_hash TEXT NOT NULL
    )""",
    """CREATE TABLE fornecedor (
        id INTEGER PRIMARY KEY, nome TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Descoberto' CHECK(status IN
            ('Descoberto', 'Em contato', 'Cotado', 'Em avaliação',
             'Fornecedor oficial', 'Descartado ou pausado')),
        cnpj TEXT, contato TEXT,
        pedido_minimo_centavos INTEGER NOT NULL DEFAULT 0
            CHECK(typeof(pedido_minimo_centavos) = 'integer' AND pedido_minimo_centavos >= 0),
        prazo TEXT, condicao_pagamento TEXT, data_ultima_cotacao TEXT,
        motivo_descarte TEXT, data_oficial TEXT,
        cnpj_verificado INTEGER NOT NULL DEFAULT 0 CHECK(cnpj_verificado IN (0, 1)),
        condicoes_verificadas INTEGER NOT NULL DEFAULT 0 CHECK(condicoes_verificadas IN (0, 1)),
        emite_nota INTEGER NOT NULL DEFAULT 0 CHECK(emite_nota IN (0, 1)),
        amostra_avaliada INTEGER NOT NULL DEFAULT 0 CHECK(amostra_avaliada IN (0, 1)),
        reposicao_confirmada INTEGER NOT NULL DEFAULT 0 CHECK(reposicao_confirmada IN (0, 1))
    )""",
    """CREATE TABLE interacao (
        id INTEGER PRIMARY KEY,
        fornecedor_id INTEGER NOT NULL REFERENCES fornecedor(id),
        data TEXT NOT NULL, canal TEXT NOT NULL, resumo TEXT NOT NULL
    )""",
    """CREATE TABLE produto (
        id INTEGER PRIMARY KEY, nome TEXT NOT NULL, familia TEXT,
        status TEXT NOT NULL DEFAULT 'Candidato',
        especificacoes_conferidas INTEGER NOT NULL DEFAULT 0 CHECK(especificacoes_conferidas IN (0, 1)),
        procedencia_conferida INTEGER NOT NULL DEFAULT 0 CHECK(procedencia_conferida IN (0, 1)),
        qualidade_conferida INTEGER NOT NULL DEFAULT 0 CHECK(qualidade_conferida IN (0, 1))
    )""",
    """CREATE TABLE sku_fornecedor (
        id INTEGER PRIMARY KEY,
        fornecedor_id INTEGER NOT NULL REFERENCES fornecedor(id),
        produto_id INTEGER NOT NULL REFERENCES produto(id), codigo TEXT NOT NULL,
        custo_unitario_centavos INTEGER NOT NULL CHECK(typeof(custo_unitario_centavos) = 'integer' AND custo_unitario_centavos >= 0),
        quantidade_minima INTEGER NOT NULL CHECK(typeof(quantidade_minima) = 'integer' AND quantidade_minima > 0),
        data_cotacao TEXT NOT NULL
    )""",
    """CREATE TABLE anuncio (
        id INTEGER PRIMARY KEY, produto_id INTEGER REFERENCES produto(id),
        marketplace TEXT NOT NULL, titulo TEXT NOT NULL, url TEXT NOT NULL,
        sinal TEXT, UNIQUE(marketplace, url)
    )""",
    """CREATE TABLE preco_observado (
        id INTEGER PRIMARY KEY, anuncio_id INTEGER NOT NULL REFERENCES anuncio(id),
        preco_centavos INTEGER NOT NULL CHECK(typeof(preco_centavos) = 'integer' AND preco_centavos >= 0),
        data TEXT NOT NULL, UNIQUE(anuncio_id, preco_centavos, data)
    )""",
    """CREATE TABLE kit (
        id INTEGER PRIMARY KEY, nome TEXT NOT NULL
    )""",
    """CREATE TABLE kit_item (
        kit_id INTEGER NOT NULL REFERENCES kit(id),
        produto_id INTEGER NOT NULL REFERENCES produto(id),
        quantidade INTEGER NOT NULL CHECK(typeof(quantidade) = 'integer' AND quantidade > 0),
        PRIMARY KEY(kit_id, produto_id)
    )""",
    """CREATE TABLE cenario_margem (
        id INTEGER PRIMARY KEY, nome TEXT NOT NULL,
        sku_fornecedor_id INTEGER REFERENCES sku_fornecedor(id),
        comissao_pct TEXT NOT NULL, tributo_pct TEXT NOT NULL, margem_alvo_pct TEXT NOT NULL,
        tarifa_fixa_centavos INTEGER NOT NULL CHECK(typeof(tarifa_fixa_centavos) = 'integer' AND tarifa_fixa_centavos >= 0),
        embalagem_centavos INTEGER NOT NULL CHECK(typeof(embalagem_centavos) = 'integer' AND embalagem_centavos >= 0),
        outros_centavos INTEGER NOT NULL CHECK(typeof(outros_centavos) = 'integer' AND outros_centavos >= 0)
    )""",
    """CREATE TABLE tarefa (
        id INTEGER PRIMARY KEY, titulo TEXT NOT NULL,
        semana INTEGER NOT NULL CHECK(typeof(semana) = 'integer' AND semana BETWEEN 1 AND 4),
        responsavel TEXT NOT NULL,
        concluida INTEGER NOT NULL DEFAULT 0 CHECK(concluida IN (0, 1))
    )""",
    "CREATE INDEX idx_interacao_fornecedor_data ON interacao(fornecedor_id, data)",
    "CREATE INDEX idx_sku_produto ON sku_fornecedor(produto_id)",
),)
