from datetime import date
from decimal import Decimal
import streamlit as st

from app.acesso import exigir_login
from app.componentes import executar, mensagem
from radar.mercado import (listar_anuncios, listar_cotacoes, pesquisar, registrar_anuncio, vincular_produto)
from radar.margem.configuracao import obter_configuracao
from radar.produtos import cotacao_antiga, listar_produtos
from radar.valores import data_br, dinheiro_texto, percentual, reais


def descricao_cotacao(c):
    return f"{c['fornecedor']} · {c['codigo']} · {data_br(c['data_cotacao'])} · {reais(Decimal(c['custo_unitario_centavos']) / 100)} · #{c['id']}"


def mostrar():
    exigir_login()
    st.title("Pesquisa de oportunidades")
    mensagem()
    produtos = {p["id"]: p for p in listar_produtos()}
    with st.expander("Cadastrar anúncio ou novo preço observado"):
        with st.form("anuncio_manual"):
            marketplace = st.text_input("Marketplace")
            titulo = st.text_input("Título do anúncio")
            url = st.text_input("URL do anúncio")
            preco = st.text_input("Preço observado (R$)")
            data = st.date_input("Data da observação", value=date.today(), max_value=date.today())
            produto = st.selectbox("Produto do anúncio", [None] + list(produtos),
                format_func=lambda i: "Vincular depois" if i is None else f"{produtos[i]['nome']} · #{i}")
            sinal = st.text_input("Sinal observado, opcional")
            salvar = st.form_submit_button("Salvar preço observado")
        if salvar:
            executar(lambda: registrar_anuncio(marketplace,titulo,url,dinheiro_texto(preco),data,produto,sinal), "Observação registrada; preços já existentes são preservados sem duplicação.")
    anuncios = listar_anuncios()
    if anuncios and produtos:
        por_id = {a["id"]: a for a in anuncios}
        with st.expander("Vincular ou corrigir produto de um anúncio"):
            anuncio_id = st.selectbox("Anúncio para vincular", list(por_id), format_func=lambda i: f"{por_id[i]['titulo']} · #{i}")
            opcoes = [None] + list(produtos)
            atual = por_id[anuncio_id]["produto_id"]
            novo = st.selectbox("Vínculo do produto", opcoes, index=opcoes.index(atual) if atual in opcoes else 0,
                format_func=lambda i: "Sem vínculo" if i is None else f"{produtos[i]['nome']} · #{i}")
            if st.button("Salvar vínculo"):
                executar(lambda: vincular_produto(anuncio_id, novo), "Vínculo atualizado.")
    if not produtos:
        st.info("Cadastre um produto em Produtos e SKUs para pesquisar margens.")
        return
    produto_id = st.selectbox("Produto pesquisado", list(produtos), format_func=lambda i: f"{produtos[i]['nome']} · #{i}")
    cotacoes = {c["id"]: c for c in listar_cotacoes(produto_id)}
    if not cotacoes:
        st.info("Registre uma cotação desse produto em Produtos e SKUs para definir o custo da pesquisa.")
        return
    cotacao_id = st.selectbox("Cotação usada como custo", list(cotacoes), format_func=lambda i: descricao_cotacao(cotacoes[i]))
    marketplaces = sorted({a["marketplace"] for a in anuncios if a["produto_id"] == produto_id})
    marketplace = st.selectbox("Filtrar marketplace", [""] + marketplaces, format_func=lambda m: m or "Todos")
    termo = st.text_input("Buscar no título dos anúncios")
    resultado = pesquisar(produto_id, cotacao_id, marketplace, termo)
    config = obter_configuracao()
    if cotacao_antiga(resultado["data_cotacao"], config.limite_cotacao_dias):
        st.warning("A cotação escolhida está antiga. Confirme o custo com o fornecedor.")
    a, b, c, d = st.columns(4)
    a.metric("Anúncios analisados", len(resultado["linhas"]))
    b.metric("Preço mediano", reais(resultado["mediana"]) if resultado["mediana"] is not None else "Sem preços")
    c.metric("Preço mínimo para o alvo", reais(resultado["preco_minimo"]) if resultado["preco_minimo"] is not None else "Alvo inviável")
    d.metric("Anúncios com margem no alvo", resultado["no_alvo"])
    pesquisa, precos, margens = st.tabs(["Pesquisa", "Preços", "Margens"])
    with pesquisa:
        st.dataframe([{"Título": r["titulo"], "Marketplace": r["marketplace"], "URL": r["url"],
            "Preço": reais(r["preco"]), "Data": data_br(r["data"]), "Sinal observado": r["sinal"] or "Não informado"}
            for r in resultado["linhas"]], hide_index=True, width="stretch")
    with precos:
        st.dataframe([{"Título": r["titulo"], "Preço": reais(Decimal(r["preco_centavos"]) / 100), "Data": data_br(r["data"])}
            for r in resultado["historico"]], hide_index=True, width="stretch")
    with margens:
        st.dataframe([{"Título": r["titulo"], "Preço": reais(r["preco"]), "Contribuição": reais(r["contribuicao"]),
            "Margem": percentual(r["margem"])} for r in resultado["linhas"]], hide_index=True, width="stretch")
    if not resultado["linhas"]:
        st.info("Nenhum anúncio vinculado corresponde aos filtros. Cadastre ou importe e vincule anúncios a este produto.")
    st.caption("Indicadores usam o preço mais recente de cada anúncio. Sinais não entram no cálculo; anúncio publicado não comprova demanda. Frete e despesas fixas não estão incluídos.")
