from decimal import Decimal
import plotly.graph_objects as go
import streamlit as st

from app.acesso import exigir_login
from app.componentes import cabecalho, executar, mensagem, selo
from app.navegacao import link
from radar.compras import obter_orcamento
from radar.painel import obter_painel, salvar_tarefa
from radar.valores import data_br, percentual, reais

# Cores das etapas do funil: da descoberta (azul) até oficial (verde); descartado em cinza.
CORES_ETAPA = ["#5b7bd5", "#3e4c9a", "#24406f", "#a64b06", "#1e7b46", "#8a96a8"]
# Para onde cada pendência leva e a cor do selo.
DESTINO = {
    "Sem resposta há mais de 5 dias": ("fornecedores", "orange"),
    "Amostra pendente": ("fornecedores", "violet"),
    "Cotação antiga": ("produtos", "yellow"),
    "Margem abaixo do alvo": ("produtos", "red"),
}
ROTULO_TELA = {"fornecedores": "Abrir Fornecedores", "produtos": "Abrir Produtos e SKUs"}


def formulario_tarefa(tarefa=None):
    t = tarefa or {}
    with st.form(f"tarefa_{t.get('id','nova')}"):
        titulo = st.text_input("Título da tarefa", t.get("titulo", ""))
        a, b = st.columns(2)
        semana = a.number_input("Semana", min_value=1,max_value=4,value=t.get("semana",1),step=1)
        responsavel = b.text_input("Responsável", t.get("responsavel", "Legacia"))
        concluida = st.checkbox("Tarefa concluída", bool(t.get("concluida")))
        salvar = st.form_submit_button("Salvar tarefa", type="primary")
    if salvar:
        executar(lambda: salvar_tarefa(titulo,semana,responsavel,concluida,t.get("id")), "Tarefa salva.")


def indicadores(painel):
    orcamento = obter_orcamento()
    total = orcamento["total_centavos"]
    a,b,c,d = st.columns(4)
    with a:
        st.metric("Fornecedores ativos",painel["fornecedores_ativos"])
        link("fornecedores", "Ver fornecedores", ":material/arrow_forward:")
    with b:
        st.metric("Candidatos levantados",painel["candidatos"])
        link("produtos", "Ver catálogo", ":material/arrow_forward:")
    with c:
        st.metric("Prontos para comprar",painel["prontos"], help="Produtos do plano de compra com os seis critérios cumpridos.")
        link("compras", "Ver decisão de compra", ":material/arrow_forward:")
    with d:
        st.metric("Orçamento comprometido",reais(Decimal(painel["comprometido_centavos"]) / 100),
                  help="Inclui os itens ainda pendentes no plano de compra.")
        st.caption(f"{percentual(Decimal(painel['comprometido_centavos']) / total)} de {reais(Decimal(total) / 100)}")


def pendencias(lista):
    with st.container(border=True):
        st.subheader("Pendências")
        if not lista:
            st.success("Nenhuma pendência identificada pelos dados e datas registrados.")
            return
        st.markdown(" ".join(selo(f"{tipo}: {sum(p['tipo'] == tipo for p in lista)}", DESTINO.get(tipo, ("", "gray"))[1])
                             for tipo in dict.fromkeys(p["tipo"] for p in lista)))
        for pessoa in sorted({p["responsavel"] for p in lista}):
            st.markdown(f"**{pessoa}**")
            for p in (p for p in lista if p["responsavel"] == pessoa):
                cor = DESTINO.get(p["tipo"], (None, "gray"))[1]
                data = f" · {data_br(p['data'])}" if p["data"] else ""
                st.markdown(f"{selo(p['tipo'], cor)} {p['referencia']}{data}")
        st.caption("Responsável sugerido pela regra: Legacia para contatos, cotações e margens; Anna para amostras.")
        a, b = st.columns(2)
        with a:
            link("fornecedores", ROTULO_TELA["fornecedores"], ":material/storefront:")
        with b:
            link("produtos", ROTULO_TELA["produtos"], ":material/inventory_2:")


def funil(etapas):
    with st.container(border=True):
        st.subheader("Funil de fornecedores")
        if not any(r["quantidade"] for r in etapas):
            st.info("Nenhum fornecedor cadastrado ainda.")
            link("fornecedores", "Cadastrar o primeiro fornecedor", ":material/add:")
            return
        figura = go.Figure(go.Bar(
            y=[r["etapa"] for r in etapas], x=[r["quantidade"] for r in etapas], orientation="h",
            marker_color=CORES_ETAPA[:len(etapas)], text=[r["quantidade"] for r in etapas],
            textposition="outside", hovertemplate="%{y}: %{x}<extra></extra>"))
        figura.update_layout(height=260, margin=dict(l=0, r=24, t=4, b=4), plot_bgcolor="white",
            paper_bgcolor="white", font=dict(family="IBM Plex Sans, Segoe UI, Arial", color="#1f2a37"),
            xaxis=dict(showgrid=True, gridcolor="#e8ecf1", dtick=1, rangemode="tozero"),
            yaxis=dict(autorange="reversed"))
        st.plotly_chart(figura, config={"displayModeBar": False})
        with st.expander("Ver como tabela"):
            st.dataframe([{"Etapa": r["etapa"], "Fornecedores": r["quantidade"]} for r in etapas],
                         hide_index=True, width="stretch")


def plano(painel):
    with st.container(border=True):
        st.subheader("Plano de 30 dias")
        tarefas = painel["tarefas"]
        total = len(tarefas)
        st.progress(painel["concluidas"] * 100 // total if total else 0,
                    text=f"{painel['concluidas']} de {total} tarefas concluídas")
        colunas = st.columns(4)
        for semana, coluna in zip(range(1, 5), colunas):
            da_semana = [t for t in tarefas if t["semana"] == semana]
            with coluna:
                st.markdown(f"**Semana {semana}** · {sum(t['concluida'] for t in da_semana)} de {len(da_semana)}")
                if not da_semana:
                    st.caption("Sem tarefas.")
                for t in da_semana:
                    estado = selo("Concluída", "green") if t["concluida"] else selo("Aberta", "blue")
                    st.markdown(f"{estado} {t['titulo']}  \n:gray[{t['responsavel']}]")
        with st.expander("Cadastrar tarefa", icon=":material/add:"):
            formulario_tarefa()
        if tarefas:
            with st.expander("Editar ou concluir tarefa", icon=":material/edit:"):
                por_id = {t["id"]: t for t in tarefas}
                tarefa_id = st.selectbox("Editar tarefa", list(por_id), format_func=lambda i: f"Semana {por_id[i]['semana']} · {por_id[i]['titulo']} · {por_id[i]['responsavel']}")
                formulario_tarefa(por_id[tarefa_id])


def mostrar():
    exigir_login()
    cabecalho("Painel", "Radar Esotérico · Tenda da Bruxa 2.0 — o que precisa de ação, o funil de "
              "fornecedores e o andamento do plano de 30 dias.")
    mensagem()
    painel = obter_painel()
    indicadores(painel)
    esquerda, direita = st.columns([1.15, 1])
    with esquerda:
        pendencias(painel["pendencias"])
    with direita:
        funil(painel["funil"])
    plano(painel)
    st.caption("Candidatos levantados conta o catálogo; prontos considera os produtos incluídos na Decisão de compra. "
               "A ferramenta mostra critérios; a decisão de compra é de vocês.")
