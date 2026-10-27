// Fornecedores: lista por etapa, ficha com checklist, condições, cotações e contatos.
// Checklist, margens e promoção vêm da API; a tela nunca decide sozinha.
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { pedir } from "../api";
import { Abas } from "../componentes/Abas";
import { Aviso, Painel as Caixa, Selo, type Tom } from "../componentes/basicos";
import { Gaveta } from "../componentes/Gaveta";
import { mensagemDeErro, useGravacao, type Executar } from "../componentes/gravacao";
import { useNotificar } from "../componentes/Notificacoes";
import { Tabela, type Coluna } from "../componentes/Tabela";
import { TabelaSkus, type LinhaSku } from "../componentes/TabelaSkus";
import { dataBr, hojeIso, percentual, reaisDeCentavos, textoDeCentavos } from "../formato";
import { enderecoDe, useRota } from "../rotas";

type Resumo = { id: number; nome: string; status: string; prazo: string | null; condicao_pagamento: string | null; data_ultima_cotacao: string | null };
type Contato = { id: number; data: string; canal: string; resumo: string; situacao_resposta: "aguardando" | "recebida" | null };
export type Ficha = Resumo & {
  cnpj: string | null;
  contato: string | null;
  pedido_minimo_centavos: number;
  data_oficial: string | null;
  motivo_descarte: string | null;
  cnpj_verificado: number;
  condicoes_verificadas: number;
  emite_nota: number;
  amostra_avaliada: number;
  reposicao_confirmada: number;
  checklist: { item: string; cumprido: boolean }[];
  margem_minima_pct: string;
  limite_cotacao_dias: number;
  skus: LinhaSku[];
  contatos: Contato[];
};

export const TOM_ETAPA: Record<string, Tom> = {
  "Descoberto": "cinza", "Em contato": "azul", "Cotado": "azul", "Em avaliação": "laranja",
  "Fornecedor oficial": "verde", "Descartado ou pausado": "vermelho",
};
const RESPOSTA = { aguardando: "Aguardando", recebida: "Recebida" } as const;
const naoInformado = (v: string | null) => (v ? v : <span className="legenda-inline">Não informado</span>);

export function Fornecedores() {
  const { filtros } = useRota();
  const [etapas, setEtapas] = useState<string[]>([]);
  const [lista, setLista] = useState<Resumo[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [cadastrando, setCadastrando] = useState(false);
  const gravacao = useGravacao();
  const notificar = useNotificar();
  const etapa = filtros.etapa ?? "";
  const fichaId = Number(filtros.ficha) || null;

  const carregar = useCallback(() => pedir<{ etapas: string[]; fornecedores: Resumo[] }>("/fornecedores").then(
    (d) => { setEtapas(d.etapas); setLista(d.fornecedores); setErro(null); },
    (e) => setErro(mensagemDeErro(e)),
  ), []);
  useEffect(() => { carregar(); }, [carregar]);

  const ir = (novos: Record<string, string>) => { window.location.hash = enderecoDe("fornecedores", { etapa, ...novos }); };

  if (erro) return <Aviso tipo="erro">{erro}</Aviso>;
  if (!lista) return <p className="legenda">Carregando fornecedores…</p>;

  const visiveis = etapa ? lista.filter((f) => f.status === etapa) : lista;
  const colunas: Coluna<Resumo>[] = [
    { chave: "nome", titulo: "Fornecedor", mostrar: (f) => f.nome, ordenar: (f) => f.nome },
    { chave: "status", titulo: "Etapa", mostrar: (f) => <Selo tom={TOM_ETAPA[f.status]}>{f.status}</Selo>,
      ordenar: (f) => etapas.indexOf(f.status) },
    { chave: "prazo", titulo: "Prazo", mostrar: (f) => naoInformado(f.prazo), ordenar: (f) => f.prazo || null },
    { chave: "pagamento", titulo: "Pagamento", mostrar: (f) => naoInformado(f.condicao_pagamento), ordenar: (f) => f.condicao_pagamento || null },
    { chave: "cotacao", titulo: "Última cotação", ordenar: (f) => f.data_ultima_cotacao,
      mostrar: (f) => (f.data_ultima_cotacao ? dataBr(f.data_ultima_cotacao) : naoInformado(null)) },
  ];

  return (
    <>
      <div className="cabecalho-acoes">
        <button type="button" className="botao botao-principal" disabled={gravacao.ocupado} onClick={() => setCadastrando(true)}>
          Cadastrar fornecedor
        </button>
      </div>
      <nav className="contadores" aria-label="Filtrar por etapa">
        <a className="contador" href={enderecoDe("fornecedores")} aria-current={!etapa ? "true" : undefined}>
          <strong>{lista.length}</strong><span>Todas as etapas</span>
        </a>
        {etapas.map((e) => (
          <a key={e} className="contador" href={enderecoDe("fornecedores", { etapa: e })} aria-current={etapa === e ? "true" : undefined}>
            <strong>{lista.filter((f) => f.status === e).length}</strong><span>{e}</span>
          </a>
        ))}
      </nav>
      <Caixa titulo={etapa ? `Fornecedores · ${etapa}` : "Fornecedores"}>
        {!lista.length ? (
          <p className="vazio">Nenhum fornecedor cadastrado. Use "Cadastrar fornecedor" para começar.</p>
        ) : (
          <Tabela titulo="Fornecedores" colunas={colunas} linhas={visiveis} chaveLinha={(f) => f.id}
            vazio="Nenhum fornecedor nesta etapa." aoClicar={(f) => ir({ ficha: String(f.id) })} />
        )}
        <p className="legenda">Clique num fornecedor para abrir a ficha. Promoção, descarte e pausa são sempre decisões de vocês.</p>
      </Caixa>

      <Gaveta aberta={cadastrando} titulo="Cadastrar fornecedor" aoFechar={() => setCadastrando(false)}>
        <FormularioFornecedor ocupado={gravacao.ocupado} aoEnviar={(dados) => gravacao.executar(async () => {
          const { id } = await pedir<{ id: number }>("/fornecedores", { corpo: dados });
          setCadastrando(false);
          notificar("Fornecedor salvo.");
          await carregar();
          ir({ ficha: String(id) });
        })} />
      </Gaveta>

      {fichaId !== null && (
        <FichaFornecedor id={fichaId} etapas={etapas} executar={gravacao.executar} ocupado={gravacao.ocupado}
          aoMudar={carregar} aoFechar={() => ir({ ficha: "" })} />
      )}
    </>
  );
}

function FichaFornecedor({ id, etapas, executar, ocupado, aoMudar, aoFechar }: {
  id: number;
  etapas: string[];
  executar: Executar;
  ocupado: boolean;
  aoMudar: () => Promise<void>;
  aoFechar: () => void;
}) {
  const [ficha, setFicha] = useState<Ficha | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const notificar = useNotificar();

  // Cada recarga gera uma versão nova; os formulários usam a versão como chave e são recriados
  // com os dados que acabaram de chegar, nunca com uma cópia anterior à gravação.
  const [versao, setVersao] = useState(0);
  // Pendências da última tentativa de promoção: ficam aqui fora para sobreviver à recarga da ficha.
  const [faltam, setFaltam] = useState<string[] | null>(null);
  const carregar = useCallback(() => pedir<Ficha>(`/fornecedores/${id}`).then(
    (f) => { setFicha(f); setVersao((v) => v + 1); setErro(null); }, (e) => setErro(mensagemDeErro(e))), [id]);
  useEffect(() => { setFicha(null); carregar(); }, [carregar]);

  // Grava, recarrega ficha e lista, e só então libera a trava.
  const gravar = (acao: () => Promise<unknown>, sucesso: string) => executar(async () => {
    await acao();
    notificar(sucesso);
    await Promise.all([carregar(), aoMudar()]);
  });

  return (
    <Gaveta aberta larga titulo={ficha?.nome ?? "Ficha do fornecedor"} aoFechar={aoFechar}>
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      {!ficha && !erro && <p className="legenda">Carregando ficha…</p>}
      {ficha && (
        <div className="pilha">
          <Cabecalho ficha={ficha} />
          <Abas rotulo="Partes da ficha" abas={[
            { titulo: "Checklist e etapa", conteudo: <Checklist key={versao} ficha={ficha} faltam={faltam} setFaltam={setFaltam} etapas={etapas} ocupado={ocupado} gravar={gravar} executar={executar} aoMudar={() => Promise.all([carregar(), aoMudar()]).then(() => {})} /> },
            { titulo: "Condições e verificações", conteudo: (
              <FormularioFornecedor key={versao} ficha={ficha} ocupado={ocupado}
                aoEnviar={(dados) => gravar(() => pedir(`/fornecedores/${id}`, { metodo: "PUT", corpo: dados }), "Fornecedor salvo.")} />
            ) },
            { titulo: `SKUs cotados (${ficha.skus.length})`, conteudo: (
              <>
                <TabelaSkus skus={ficha.skus} limiteDias={ficha.limite_cotacao_dias} semFornecedor />
                <a href={enderecoDe("produtos")}>Lançar ou renovar cotações em Produtos e SKUs</a>
              </>
            ) },
            { titulo: `Contatos (${ficha.contatos.length})`, conteudo: (
              <Contatos key={versao} ficha={ficha} ocupado={ocupado}
                aoEnviar={(dados) => gravar(() => pedir(`/fornecedores/${id}/contatos`, { corpo: dados }), "Contato registrado.")} />
            ) },
          ]} />
        </div>
      )}
    </Gaveta>
  );
}

function Cabecalho({ ficha }: { ficha: Ficha }) {
  const cumpridos = ficha.checklist.filter((c) => c.cumprido).length;
  const completo = cumpridos === ficha.checklist.length;
  return (
    <div>
      <ul className="selos">
        <li><Selo tom={TOM_ETAPA[ficha.status]}>{ficha.status}</Selo></li>
        <li><Selo tom={completo ? "verde" : "laranja"}>{cumpridos} de {ficha.checklist.length} itens do checklist</Selo></li>
      </ul>
      <dl className="fatos">
        <div><dt>Pedido mínimo</dt><dd>{reaisDeCentavos(ficha.pedido_minimo_centavos)}</dd></div>
        <div><dt>Prazo</dt><dd>{naoInformado(ficha.prazo)}</dd></div>
        <div><dt>Pagamento</dt><dd>{naoInformado(ficha.condicao_pagamento)}</dd></div>
        <div><dt>Última cotação</dt><dd>{ficha.data_ultima_cotacao ? dataBr(ficha.data_ultima_cotacao) : naoInformado(null)}</dd></div>
      </dl>
      {ficha.data_oficial && <p className="legenda">Promovido a oficial em {dataBr(ficha.data_oficial)}.</p>}
      {ficha.motivo_descarte && <p className="legenda">Último motivo de descarte ou pausa: {ficha.motivo_descarte}</p>}
    </div>
  );
}

function Checklist({ ficha, faltam, setFaltam, etapas, ocupado, gravar, executar, aoMudar }: {
  ficha: Ficha;
  faltam: string[] | null;
  setFaltam: (pendencias: string[] | null) => void;
  etapas: string[];
  ocupado: boolean;
  gravar: (acao: () => Promise<unknown>, sucesso: string) => Promise<unknown>;
  executar: Executar;
  aoMudar: () => Promise<void>;
}) {
  const opcoes = etapas.filter((e) => e !== "Fornecedor oficial");
  const [etapa, setEtapa] = useState(opcoes.includes(ficha.status) ? ficha.status : opcoes[0]);
  const [motivo, setMotivo] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const notificar = useNotificar();

  async function promover() {
    setErro(null);
    setFaltam(null);
    try {
      await executar(async () => {
        const r = await pedir<{ promovido: boolean; pendencias: string[] }>(`/fornecedores/${ficha.id}/promover`, { metodo: "POST" });
        if (r.promovido) notificar("Fornecedor promovido a oficial.");
        else setFaltam(r.pendencias);
        await aoMudar();
      });
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  }

  async function mudarEtapa(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    try {
      await gravar(() => pedir(`/fornecedores/${ficha.id}/etapa`, { corpo: { etapa, motivo } }), "Etapa atualizada.");
      setMotivo("");
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  }

  return (
    <div className="pilha">
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      <div>
        <h3 className="subtitulo">Checklist de promoção</h3>
        <p className="legenda">Exige margem de pelo menos {percentual(ficha.margem_minima_pct)} em três produtos distintos.</p>
      </div>
      <ul className="lista-checklist">
        {ficha.checklist.map((c) => (
          <li key={c.item}><Selo tom={c.cumprido ? "verde" : "laranja"}>{c.cumprido ? "Cumprido" : "Pendente"}</Selo> {c.item}</li>
        ))}
      </ul>
      {faltam && (
        <Aviso tipo="erro" titulo="Promoção não realizada. Falta cumprir:">
          <ul>{faltam.map((p) => <li key={p}>{p}</li>)}</ul>
        </Aviso>
      )}
      <div>
        <button type="button" className="botao botao-principal" onClick={promover} disabled={ocupado}>
          Promover a fornecedor oficial
        </button>
        <p className="legenda">O sistema nunca promove sozinho: o botão confere o checklist e só muda a etapa se tudo estiver cumprido.</p>
      </div>
      <form className="formulario grupo" onSubmit={mudarEtapa}>
        <h3 className="subtitulo">Mudar etapa de acompanhamento</h3>
        <div className="campos-2">
          <label>Etapa de acompanhamento
            <select value={etapa} onChange={(e) => setEtapa(e.target.value)}>
              {opcoes.map((e) => <option key={e}>{e}</option>)}
            </select>
          </label>
          <label>Motivo para descartar ou pausar
            <input value={motivo} onChange={(e) => setMotivo(e.target.value)} required={etapa === "Descartado ou pausado"} />
          </label>
        </div>
        <div><button type="submit" className="botao" disabled={ocupado}>Alterar etapa</button></div>
      </form>
    </div>
  );
}

type DadosFornecedor = {
  nome: string; cnpj: string; contato: string; pedido_minimo: string; prazo: string; condicao_pagamento: string;
  cnpj_verificado: boolean; condicoes_verificadas: boolean; emite_nota: boolean; amostra_avaliada: boolean; reposicao_confirmada: boolean;
};

const VERIFICACOES: [keyof DadosFornecedor, string][] = [
  ["cnpj_verificado", "CNPJ verificado"],
  ["condicoes_verificadas", "Condições comerciais verificadas"],
  ["emite_nota", "Emite nota fiscal"],
  ["amostra_avaliada", "Amostra avaliada pela Anna (especificações, procedência e qualidade)"],
  ["reposicao_confirmada", "Reposição confirmada"],
];

export function FormularioFornecedor({ ficha, ocupado, aoEnviar }: {
  ficha?: Ficha;
  ocupado: boolean;
  aoEnviar: (dados: DadosFornecedor) => Promise<unknown>;
}) {
  const [dados, setDados] = useState<DadosFornecedor>(() => ({
    nome: ficha?.nome ?? "", cnpj: ficha?.cnpj ?? "", contato: ficha?.contato ?? "",
    pedido_minimo: textoDeCentavos(ficha?.pedido_minimo_centavos ?? 0),
    prazo: ficha?.prazo ?? "", condicao_pagamento: ficha?.condicao_pagamento ?? "",
    cnpj_verificado: !!ficha?.cnpj_verificado, condicoes_verificadas: !!ficha?.condicoes_verificadas,
    emite_nota: !!ficha?.emite_nota, amostra_avaliada: !!ficha?.amostra_avaliada, reposicao_confirmada: !!ficha?.reposicao_confirmada,
  }));
  const [erro, setErro] = useState<string | null>(null);
  const campo = (chave: keyof DadosFornecedor) => ({
    value: dados[chave] as string,
    onChange: (e: { target: { value: string } }) => setDados({ ...dados, [chave]: e.target.value }),
  });

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    try {
      await aoEnviar(dados);
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      <div className="campos-2">
        <label>Nome do fornecedor<input required {...campo("nome")} /></label>
        <label>CNPJ<input {...campo("cnpj")} /></label>
        <label>Contato<input {...campo("contato")} /></label>
        <label>Pedido mínimo (R$)<input inputMode="decimal" {...campo("pedido_minimo")} /></label>
        <label>Prazo<input {...campo("prazo")} /></label>
        <label>Condição de pagamento<input {...campo("condicao_pagamento")} /></label>
      </div>
      <fieldset className="grupo">
        <legend>Verificações manuais</legend>
        <p className="legenda">Confirmações feitas por vocês após verificar as informações.</p>
        {VERIFICACOES.map(([chave, rotulo]) => (
          <label key={chave} className="tarefa">
            <input type="checkbox" checked={dados[chave] as boolean} onChange={(e) => setDados({ ...dados, [chave]: e.target.checked })} />
            {rotulo}
          </label>
        ))}
      </fieldset>
      <div>
        <button type="submit" className="botao botao-principal" disabled={ocupado}>{ocupado ? "Salvando…" : "Salvar fornecedor"}</button>
      </div>
    </form>
  );
}

type DadosContato = { data: string; canal: string; resumo: string; situacao_resposta: string | null };

function Contatos({ ficha, ocupado, aoEnviar }: { ficha: Ficha; ocupado: boolean; aoEnviar: (d: DadosContato) => Promise<unknown> }) {
  const vazio = (): DadosContato => ({ data: hojeIso(), canal: "", resumo: "", situacao_resposta: null });
  const [dados, setDados] = useState(vazio);
  const [erro, setErro] = useState<string | null>(null);
  const colunas: Coluna<Contato>[] = [
    { chave: "data", titulo: "Data", mostrar: (c) => dataBr(c.data), ordenar: (c) => c.data },
    { chave: "canal", titulo: "Canal", mostrar: (c) => c.canal, ordenar: (c) => c.canal },
    { chave: "resumo", titulo: "Resumo", mostrar: (c) => c.resumo },
    { chave: "resposta", titulo: "Resposta", ordenar: (c) => c.situacao_resposta,
      mostrar: (c) => (c.situacao_resposta ? RESPOSTA[c.situacao_resposta] : "Não informada") },
  ];

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    try {
      await aoEnviar(dados);
      setDados(vazio());
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  }

  return (
    <div className="pilha">
      <Tabela titulo="Histórico de contatos" colunas={colunas} linhas={ficha.contatos} chaveLinha={(c) => c.id}
        vazio="Nenhum contato registrado." />
      <form className="formulario grupo" onSubmit={enviar}>
        <h3 className="subtitulo">Registrar contato</h3>
        {erro && <Aviso tipo="erro">{erro}</Aviso>}
        <div className="campos-2">
          <label>Data do contato
            <input type="date" required max={hojeIso()} value={dados.data} onChange={(e) => setDados({ ...dados, data: e.target.value })} />
          </label>
          <label>Canal<input required value={dados.canal} onChange={(e) => setDados({ ...dados, canal: e.target.value })} /></label>
          <label>Situação da resposta
            <select value={dados.situacao_resposta ?? ""} onChange={(e) => setDados({ ...dados, situacao_resposta: e.target.value || null })}>
              <option value="">Não informar</option>
              <option value="aguardando">Aguardando resposta</option>
              <option value="recebida">Resposta recebida</option>
            </select>
          </label>
        </div>
        <label>Resumo do contato
          <textarea required rows={3} value={dados.resumo} onChange={(e) => setDados({ ...dados, resumo: e.target.value })} />
        </label>
        <div><button type="submit" className="botao botao-principal" disabled={ocupado}>Adicionar contato</button></div>
      </form>
    </div>
  );
}
