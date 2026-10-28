// Painel: o que precisa de ação, funil de fornecedores e plano de 30 dias.
// Todos os números vêm prontos de GET /api/painel; aqui só se formata e se desenha.
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { ErroApi, pedir } from "../api";
import { Aviso, Indicador, Painel as Caixa, Selo, type Tom } from "../componentes/basicos";
import { Gaveta } from "../componentes/Gaveta";
import { useNotificar } from "../componentes/Notificacoes";
import { dataBr, percentual, reaisDeCentavos } from "../formato";
import { enderecoDe } from "../rotas";
import { Dica } from "../componentes/Dica";

export type Tarefa = { id: number; titulo: string; semana: number; responsavel: string; concluida: number };
type Pendencia = { tipo: string; referencia: string; data: string | null; responsavel: string };
export type DadosPainel = {
  fornecedores_ativos: number;
  candidatos: number;
  prontos: number;
  comprometido_centavos: number;
  comprometido_pct: string | null;
  orcamento_total_centavos: number;
  tarefas: Tarefa[];
  concluidas: number;
  funil: { etapa: string; quantidade: number }[];
  pendencias: Pendencia[];
};

// Para onde cada tipo de pendência leva e a cor do selo.
const DESTINO: Record<string, { pagina: string; tom: Tom }> = {
  "Sem resposta há mais de 5 dias": { pagina: "fornecedores", tom: "laranja" },
  "Amostra pendente": { pagina: "fornecedores", tom: "azul" },
  "Cotação antiga": { pagina: "produtos", tom: "amarelo" },
  "Margem abaixo do alvo": { pagina: "produtos", tom: "vermelho" },
};
const CORES_ETAPA = ["#5b7bd5", "#3e4c9a", "#24406f", "#a64b06", "#1e7b46", "#8a96a8"];

export function Painel() {
  const [dados, setDados] = useState<DadosPainel | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  // Devolve a promessa para quem salvou poder esperar os dados novos chegarem.
  const carregar = useCallback(() =>
    pedir<DadosPainel>("/painel").then(
      (d) => { setDados(d); setErro(null); },
      (e) => setErro(e instanceof ErroApi ? e.message : "Não foi possível carregar o painel."),
    ), []);
  useEffect(() => { carregar(); }, [carregar]);

  if (erro) return <Aviso tipo="erro">{erro}</Aviso>;
  if (!dados) return <p className="legenda">Carregando o painel…</p>;

  return (
    <>
      <Indicadores dados={dados} />
      <div className="grade-2">
        <Pendencias lista={dados.pendencias} />
        <Funil etapas={dados.funil} />
      </div>
      <Plano tarefas={dados.tarefas} concluidas={dados.concluidas} aoSalvar={carregar} />
      <p className="legenda">
        Candidatos levantados conta o catálogo; prontos considera os produtos incluídos na Decisão de compra.
        A ferramenta mostra critérios; a decisão de compra é de vocês.
      </p>
    </>
  );
}

function Indicadores({ dados }: { dados: DadosPainel }) {
  const fracao = dados.comprometido_pct === null ? "" : `${percentual(dados.comprometido_pct)} de `;
  return (
    <div className="grade-4">
      <Indicador rotulo="Fornecedores ativos" valor={dados.fornecedores_ativos} />
      <Indicador rotulo="Candidatos levantados" valor={dados.candidatos} />
      <Indicador rotulo="Prontos para comprar" valor={dados.prontos} tom="verde"
        detalhe="Produtos do plano com os seis critérios cumpridos" />
      <Indicador rotulo="Orçamento comprometido" valor={reaisDeCentavos(dados.comprometido_centavos)}
        detalhe={`${fracao}${reaisDeCentavos(dados.orcamento_total_centavos)}, inclui itens pendentes`} />
    </div>
  );
}

function Pendencias({ lista }: { lista: Pendencia[] }) {
  const tipos = [...new Set(lista.map((p) => p.tipo))];
  const pessoas = [...new Set(lista.map((p) => p.responsavel))].sort((a, b) => a.localeCompare(b, "pt-BR"));
  return (
    <Caixa titulo="Pendências">
      {!lista.length ? (
        <Aviso tipo="sucesso">Nenhuma pendência identificada pelos dados e datas registrados.</Aviso>
      ) : (
        <div className="pilha">
          <ul className="selos" aria-label="Resumo por tipo">
            {tipos.map((tipo) => (
              <li key={tipo}>
                <a className="selo-link" href={enderecoDe(DESTINO[tipo]?.pagina ?? "painel")}>
                  <Selo tom={DESTINO[tipo]?.tom ?? "cinza"}>{tipo}: {lista.filter((p) => p.tipo === tipo).length}</Selo>
                </a>
              </li>
            ))}
          </ul>
          {pessoas.map((pessoa) => (
            <div key={pessoa}>
              <h3 className="subtitulo">{pessoa}</h3>
              <ul className="lista-pendencias">
                {lista.filter((p) => p.responsavel === pessoa).map((p, i) => (
                  <li key={`${p.tipo}-${p.referencia}-${i}`}>
                    <Selo tom={DESTINO[p.tipo]?.tom ?? "cinza"}>{p.tipo}</Selo>{" "}
                    <a href={enderecoDe(DESTINO[p.tipo]?.pagina ?? "painel")}>{p.referencia}</a>
                    {p.data && <span className="legenda-inline"> · {dataBr(p.data)}</span>}
                  </li>
                ))}
              </ul>
            </div>
          ))}
          <p className="legenda">Responsável sugerido pela regra: Legacia para contatos, cotações e margens; Anna para amostras.</p>
        </div>
      )}
    </Caixa>
  );
}

function Funil({ etapas }: { etapas: DadosPainel["funil"] }) {
  const maior = Math.max(0, ...etapas.map((e) => e.quantidade));
  if (!maior) {
    return (
      <Caixa titulo="Funil de fornecedores">
        <p className="vazio">Nenhum fornecedor cadastrado ainda.</p>
        <a href={enderecoDe("fornecedores")}>Cadastrar o primeiro fornecedor</a>
      </Caixa>
    );
  }
  const [rotulo, barra, linha] = [150, 260, 30];
  const descricao = etapas.map((e) => `${e.etapa}: ${e.quantidade}`).join("; ");
  return (
    <Caixa titulo="Funil de fornecedores">
      <svg className="grafico" viewBox={`0 0 ${rotulo + barra + 40} ${etapas.length * linha}`} role="img"
        aria-label={`Fornecedores por etapa. ${descricao}.`}>
        {etapas.map((e, i) => {
          const largura = (e.quantidade * barra) / maior;
          const y = i * linha;
          return (
            <a key={e.etapa} href={enderecoDe("fornecedores", { etapa: e.etapa })} aria-label={`${e.etapa}: ${e.quantidade}`}>
              <text x={rotulo - 8} y={y + 19} textAnchor="end" className="grafico-rotulo">{e.etapa}</text>
              <rect x={rotulo} y={y + 6} width={Math.max(largura, e.quantidade ? 2 : 0)} height={18} rx={3}
                fill={CORES_ETAPA[i % CORES_ETAPA.length]} />
              <text x={rotulo + largura + 6} y={y + 19} className="grafico-valor">{e.quantidade}</text>
            </a>
          );
        })}
      </svg>
      <details className="alternativa">
        <summary>Ver como tabela</summary>
        <table className="tabela">
          <thead><tr><th scope="col">Etapa</th><th scope="col" className="direita">Fornecedores</th></tr></thead>
          <tbody>
            {etapas.map((e) => <tr key={e.etapa}><td>{e.etapa}</td><td className="direita">{e.quantidade}</td></tr>)}
          </tbody>
        </table>
      </details>
    </Caixa>
  );
}

type CorpoTarefa = { titulo: string; semana: number; responsavel: string; concluida: boolean };

function Plano({ tarefas, concluidas, aoSalvar }: { tarefas: Tarefa[]; concluidas: number; aoSalvar: () => Promise<void> }) {
  const notificar = useNotificar();
  const [editando, setEditando] = useState<Tarefa | "nova" | null>(null);
  // Uma trava só para o plano: liga no início de qualquer gravação e só desliga depois que o
  // painel recarrega, mesmo que a gaveta seja fechada no meio. Assim nada parte de dados antigos.
  const [ocupado, setOcupado] = useState(false);
  const trava = useRef(false);
  const gavetaAberta = useRef(false);
  gavetaAberta.current = editando !== null;
  const total = tarefas.length;

  async function gravar(caminho: string, metodo: "POST" | "PUT", corpo: CorpoTarefa, sucesso: string, daGaveta: boolean) {
    if (trava.current) return;
    trava.current = true;
    setOcupado(true);
    try {
      await pedir(caminho, { metodo, corpo });
      if (daGaveta) setEditando(null);
      notificar(sucesso);
      await aoSalvar();
    } catch (e) {
      const mensagem = e instanceof ErroApi ? e.message : "Não foi possível salvar.";
      // Com a gaveta aberta o erro aparece nela; se já foi fechada, vira notificação.
      if (daGaveta && gavetaAberta.current) throw new Error(mensagem);
      notificar(mensagem, "erro");
    } finally {
      trava.current = false;
      setOcupado(false);
    }
  }

  const alternar = (t: Tarefa) => gravar(`/tarefas/${t.id}`, "PUT",
    { titulo: t.titulo, semana: t.semana, responsavel: t.responsavel, concluida: !t.concluida },
    t.concluida ? "Tarefa reaberta." : "Tarefa concluída.", false);

  const salvarDaGaveta = (tarefa: Tarefa | undefined, corpo: CorpoTarefa) => tarefa
    ? gravar(`/tarefas/${tarefa.id}`, "PUT", corpo, "Tarefa salva.", true)
    : gravar("/tarefas", "POST", corpo, "Tarefa salva.", true);

  return (
    <Caixa titulo="Plano de 30 dias"
      acoes={<button type="button" className="botao" onClick={() => setEditando("nova")} disabled={ocupado}>Cadastrar tarefa</button>}>
      <div className="progresso-rotulo">{concluidas} de {total} tarefas concluídas</div>
      <progress className="progresso" max={total || 1} value={concluidas} aria-label="Andamento do plano de 30 dias" />
      <div className="grade-4 semanas">
        {[1, 2, 3, 4].map((semana) => {
          const daSemana = tarefas.filter((t) => t.semana === semana);
          return (
            <section key={semana} aria-label={`Semana ${semana}`}>
              <h3 className="subtitulo">Semana {semana} · {daSemana.filter((t) => t.concluida).length} de {daSemana.length}</h3>
              {!daSemana.length && <p className="vazio">Sem tarefas.</p>}
              <ul className="lista-tarefas">
                {daSemana.map((t) => (
                  <li key={t.id}>
                    <label className="tarefa">
                      <input type="checkbox" checked={!!t.concluida} onChange={() => alternar(t)}
                        disabled={ocupado} />
                      <span className={t.concluida ? "riscado" : undefined}>{t.titulo}</span>
                    </label>
                    <div className="tarefa-pe">
                      <span className="legenda-inline">{t.responsavel}</span>
                      <button type="button" className="botao-discreto link" onClick={() => setEditando(t)}
                        disabled={ocupado}
                        aria-label={`Editar ${t.titulo}`}>Editar</button>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
      </div>
      <Gaveta aberta={editando !== null} titulo={editando === "nova" ? "Cadastrar tarefa" : "Editar tarefa"}
        aoFechar={() => setEditando(null)}>
        {editando !== null && (
          <FormularioTarefa tarefa={editando === "nova" ? undefined : editando}
            ocupado={ocupado} aoEnviar={(corpo) => salvarDaGaveta(editando === "nova" ? undefined : editando, corpo)} />
        )}
      </Gaveta>
    </Caixa>
  );
}

export function FormularioTarefa({ tarefa, ocupado, aoEnviar }: {
  tarefa?: Tarefa;
  ocupado: boolean;
  aoEnviar: (corpo: CorpoTarefa) => Promise<void>;
}) {
  const [titulo, setTitulo] = useState(tarefa?.titulo ?? "");
  const [semana, setSemana] = useState(tarefa?.semana ?? 1);
  const [responsavel, setResponsavel] = useState(tarefa?.responsavel ?? "Legacia");
  const [concluida, setConcluida] = useState(!!tarefa?.concluida);
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (ocupado) return;
    setErro(null);
    try {
      await aoEnviar({ titulo, semana, responsavel, concluida });
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível salvar.");
    }
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      <label><span className="rotulo">Título da tarefa<Dica de="Título da tarefa" /></span><input value={titulo} onChange={(e) => setTitulo(e.target.value)} required /></label>
      <label><span className="rotulo">Semana<Dica de="Semana" /></span>
        <select value={semana} onChange={(e) => setSemana(Number(e.target.value))}>
          {[1, 2, 3, 4].map((s) => <option key={s} value={s}>Semana {s}</option>)}
        </select>
      </label>
      <label><span className="rotulo">Responsável<Dica de="Responsável" /></span><input value={responsavel} onChange={(e) => setResponsavel(e.target.value)} required /></label>
      <label className="tarefa">
        <input type="checkbox" checked={concluida} onChange={(e) => setConcluida(e.target.checked)} />
        Tarefa concluída<Dica de="Tarefa concluída" />
      </label>
      <button type="submit" className="botao botao-principal" disabled={ocupado}>
        {ocupado ? "Salvando…" : "Salvar tarefa"}
      </button>
    </form>
  );
}
