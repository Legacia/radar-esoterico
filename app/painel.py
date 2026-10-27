from decimal import Decimal
import plotly.graph_objects as go
import streamlit as st

from app.acesso import exigir_login
from app.componentes import executar, mensagem
from radar.painel import obter_painel, salvar_tarefa
from radar.valores import data_br, reais


def formulario_tarefa(tarefa=None):
    t = tarefa or {}
    with st.form(f"tarefa_{t.get('id','nova')}"):
        titulo = st.text_input("Título da tarefa", t.get("titulo", ""))
        semana = st.number_input("Semana", min_value=1,max_value=4,value=t.get("semana",1),step=1)
        responsavel = st.text_input("Responsável", t.get("responsavel", "Legacia"))
        concluida = st.checkbox("Tarefa concluída", bool(t.get("concluida")))
        salvar = st.form_submit_button("Salvar tarefa")
    if salvar:
        executar(lambda: salvar_tarefa(titulo,semana,responsavel,concluida,t.get("id")), "Tarefa salva.")


def mostrar():
    exigir_login()
    st.title("Painel")
    st.caption("Radar Esotérico · Tenda da Bruxa 2.0")
    mensagem()
    painel = obter_painel()
    a,b,c,d = st.columns(4)
    a.metric("Fornecedores ativos",painel["fornecedores_ativos"])
    b.metric("Candidatos levantados",painel["candidatos"])
    c.metric("Prontos para comprar",painel["prontos"])
    d.metric("Orçamento comprometido",reais(Decimal(painel["comprometido_centavos"]) / 100))
    st.caption("Candidatos levantados conta o catálogo; prontos considera os produtos incluídos na Decisão de compra.")
    st.subheader("Plano de 30 dias")
    total = len(painel["tarefas"])
    st.progress(painel["concluidas"] * 100 // total if total else 0,
                text=f"{painel['concluidas']} de {total} tarefas concluídas")
    for semana in range(1,5):
        tarefas = [t for t in painel["tarefas"] if t["semana"] == semana]
        st.write(f"Semana {semana}: {sum(t['concluida'] for t in tarefas)} de {len(tarefas)} concluídas")
    with st.expander("Cadastrar tarefa"):
        formulario_tarefa()
    if painel["tarefas"]:
        por_id = {t["id"]: t for t in painel["tarefas"]}
        tarefa_id = st.selectbox("Editar tarefa", list(por_id), format_func=lambda i: f"Semana {por_id[i]['semana']} · {por_id[i]['titulo']} · {por_id[i]['responsavel']}")
        formulario_tarefa(por_id[tarefa_id])
    st.subheader("Funil de fornecedores")
    st.plotly_chart(go.Figure(go.Funnel(y=[r["etapa"] for r in painel["funil"]],
        x=[r["quantidade"] for r in painel["funil"]])), width="stretch")
    st.subheader("Pendências")
    if painel["pendencias"]:
        st.dataframe([{"Pendência": p["tipo"], "Referência": p["referencia"], "Data": data_br(p["data"]),
            "Responsável sugerido": p["responsavel"]} for p in painel["pendencias"]], hide_index=True,width="stretch")
    else:
        st.info("Nenhuma pendência identificada pelos dados e datas registrados.")
