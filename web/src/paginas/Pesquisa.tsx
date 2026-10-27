// Pesquisa de oportunidades: preços observados nos marketplaces comparados com o custo de uma cotação.
// Simulação livre: usa a margem-alvo configurada. Sinais de procura ficam separados do cálculo de margem.
// Margens, mediana e preço mínimo vêm prontos de GET /api/pesquisa.
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { pedir } from "../api";
import { Abas } from "../componentes/Abas";
import { Aviso, Indicador, Painel as Caixa } from "../componentes/basicos";
import { Gaveta } from "../componentes/Gaveta";
import { mensagemDeErro, useGravacao } from "../componentes/gravacao";
import { useNotificar } from "../componentes/Notificacoes";
import { Tabela, type Coluna } from "../componentes/Tabela";
import { dataBr, hojeIso, percentual, reais, reaisDeCentavos } from "../formato";
import { enderecoDe, useRota } from "../rotas";

type AnuncioResumo = { id: number; marketplace: string; titulo: string; url: string; produto_id: number | null; produto: string | null };
type Opcao = { id: number; nome: string };
type Cotacao = { id: number; fornecedor: string; codigo: string; data_cotacao: string; custo_centavos: number };
type Linha = {
  id: number; marketplace: string; titulo: string; url: string; sinal: string | null;
  preco_centavos: number; data: string; contribuicao: string; margem_pct: string;
};
export type Resultado = {
  linhas: Linha[];
  historico: { anuncio_id: number; titulo: string; preco_centavos: number; data: string }[];
  mediana: string | null;
  preco_minimo: string | null;
  no_alvo: number;
  margem_alvo_pct: string;
  custo_centavos: number;
  data_cotacao: string;
  cotacao_antiga: boolean;
  marketplaces: string[];
};

export function Pesquisa() {
  const { filtros } = useRota();
  const [base, setBase] = useState<{ anuncios: AnuncioResumo[]; produtos: Opcao[] } | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [gaveta, setGaveta] = useState<"anuncio" | "vinculo" | null>(null);
  const gravacao = useGravacao();
  const notificar = useNotificar();

  const carregar = useCallback(() => pedir<{ anuncios: AnuncioResumo[]; produtos: Opcao[] }>("/pesquisa/anuncios").then(
    (d) => { setBase(d); setErro(null); }, (e) => setErro(mensagemDeErro(e))), []);
  useEffect(() => { carregar(); }, [carregar]);

  if (erro) return <Aviso tipo="erro">{erro}</Aviso>;
  if (!base) return <p className="legenda">Carregando anúncios…</p>;

  const semVinculo = base.anuncios.filter((a) => a.produto_id === null).length;
  const produtoId = base.produtos.some((p) => String(p.id) === filtros.produto) ? Number(filtros.produto) : base.produtos[0]?.id;

  return (
    <>
      <div className="cabecalho-acoes">
        <button type="button" className="botao botao-principal" disabled={gravacao.ocupado} onClick={() => setGaveta("anuncio")}>
          Cadastrar anúncio ou preço
        </button>
        {base.anuncios.length > 0 && base.produtos.length > 0 && (
          <button type="button" className="botao" disabled={gravacao.ocupado} onClick={() => setGaveta("vinculo")}>
            Vincular anúncio a produto{semVinculo ? ` (${semVinculo} sem vínculo)` : ""}
          </button>
        )}
        <a href={enderecoDe("importar")}>Muitos anúncios? Importe um CSV</a>
      </div>

      {produtoId === undefined ? (
        <Aviso>Cadastre um produto em <a href={enderecoDe("produtos")}>Produtos e SKUs</a> para pesquisar margens.</Aviso>
      ) : (
        <Resultados key={produtoId} produtos={base.produtos} produtoId={produtoId} filtros={filtros} rodada={gravacao.concluidas} />
      )}

      <Gaveta aberta={gaveta === "anuncio"} titulo="Cadastrar anúncio ou novo preço observado" aoFechar={() => setGaveta(null)}>
        <FormularioAnuncio produtos={base.produtos} produtoInicial={produtoId ?? null} ocupado={gravacao.ocupado}
          aoEnviar={(dados) => gravacao.executar(async () => {
            const r = await pedir<{ novo_preco: boolean }>("/pesquisa/anuncios", { corpo: dados });
            setGaveta(null);
            notificar(r.novo_preco ? "Observação registrada." : "Esse preço já estava registrado nessa data; nada foi duplicado.");
            await carregar();
          })} />
      </Gaveta>

      <Gaveta aberta={gaveta === "vinculo"} titulo="Vincular ou corrigir produto de um anúncio" aoFechar={() => setGaveta(null)}>
        <FormularioVinculo anuncios={base.anuncios} produtos={base.produtos} ocupado={gravacao.ocupado}
          aoEnviar={(anuncioId, produto) => gravacao.executar(async () => {
            await pedir(`/pesquisa/anuncios/${anuncioId}/produto`, { metodo: "PUT", corpo: { produto_id: produto } });
            setGaveta(null);
            notificar("Vínculo atualizado.");
            await carregar();
          })} />
      </Gaveta>
    </>
  );
}

function Resultados({ produtos, produtoId, filtros, rodada }: {
  produtos: Opcao[];
  produtoId: number;
  filtros: Record<string, string>;
  rodada: number;
}) {
  const [cotacoes, setCotacoes] = useState<Cotacao[] | null>(null);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [termo, setTermo] = useState(filtros.termo ?? "");
  const ultima = useRef(0);

  const ir = (novos: Record<string, string>) => {
    window.location.hash = enderecoDe("pesquisa", {
      produto: String(produtoId), cotacao: filtros.cotacao ?? "", marketplace: filtros.marketplace ?? "",
      termo: filtros.termo ?? "", ...novos });
  };

  useEffect(() => {
    pedir<Cotacao[]>(`/pesquisa/cotacoes?produto_id=${produtoId}`).then(setCotacoes, (e) => setErro(mensagemDeErro(e)));
  }, [produtoId, rodada]);

  const cotacaoId = cotacoes?.some((c) => String(c.id) === filtros.cotacao) ? Number(filtros.cotacao) : cotacoes?.[0]?.id;
  const marketplace = filtros.marketplace ?? "";
  const termoFiltro = filtros.termo ?? "";

  // Só a resposta da consulta mais recente aparece, mesmo com filtros trocados rapidamente.
  useEffect(() => {
    if (cotacaoId === undefined) return;
    const consulta = ++ultima.current;
    const busca = new URLSearchParams({ produto_id: String(produtoId), cotacao_id: String(cotacaoId), marketplace, termo: termoFiltro });
    pedir<Resultado>(`/pesquisa?${busca}`).then(
      (r) => { if (consulta === ultima.current) { setResultado(r); setErro(null); } },
      (e) => { if (consulta === ultima.current) setErro(mensagemDeErro(e)); });
  }, [produtoId, cotacaoId, marketplace, termoFiltro, rodada]);

  function buscar(evento: FormEvent) {
    evento.preventDefault();
    ir({ termo });
  }

  return (
    <>
      <Caixa titulo="O que pesquisar">
        <form className="formulario" onSubmit={buscar}>
          <div className="campos-2">
            <label>Produto pesquisado
              <select value={produtoId} onChange={(e) => ir({ produto: e.target.value, cotacao: "", marketplace: "" })}>
                {produtos.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
              </select>
            </label>
            <label>Cotação usada como custo
              <select value={cotacaoId ?? ""} disabled={!cotacoes?.length} onChange={(e) => ir({ cotacao: e.target.value })}>
                {!cotacoes?.length && <option value="">Sem cotações</option>}
                {cotacoes?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.fornecedor} · {c.codigo} · {dataBr(c.data_cotacao)} · {reaisDeCentavos(c.custo_centavos)}
                  </option>
                ))}
              </select>
            </label>
            <label>Filtrar marketplace
              <select value={marketplace} onChange={(e) => ir({ marketplace: e.target.value })}>
                <option value="">Todos</option>
                {resultado?.marketplaces.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </label>
            <label>Buscar no título dos anúncios
              <span className="campo-com-botao">
                <input type="search" value={termo} onChange={(e) => setTermo(e.target.value)} />
                <button type="submit" className="botao">Buscar</button>
              </span>
            </label>
          </div>
        </form>
      </Caixa>

      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      {cotacoes && !cotacoes.length && (
        <Aviso>Registre uma cotação desse produto em <a href={enderecoDe("produtos", { ficha: String(produtoId) })}>Produtos e SKUs</a> para definir o custo da pesquisa.</Aviso>
      )}
      {resultado && cotacoes?.length ? <Painel resultado={resultado} /> : null}
    </>
  );
}

function Painel({ resultado }: { resultado: Resultado }) {
  const linhas: Coluna<Linha>[] = [
    { chave: "titulo", titulo: "Título", mostrar: (l) => l.titulo, ordenar: (l) => l.titulo },
    { chave: "marketplace", titulo: "Marketplace", mostrar: (l) => l.marketplace, ordenar: (l) => l.marketplace },
    { chave: "url", titulo: "Anúncio", mostrar: (l) => <a href={l.url} target="_blank" rel="noopener noreferrer">Abrir anúncio</a> },
    { chave: "preco", titulo: "Preço", alinhar: "direita", mostrar: (l) => reaisDeCentavos(l.preco_centavos), ordenar: (l) => l.preco_centavos },
    { chave: "data", titulo: "Data", mostrar: (l) => dataBr(l.data), ordenar: (l) => l.data },
    { chave: "sinal", titulo: "Sinal observado", mostrar: (l) => l.sinal || <span className="legenda-inline">Não informado</span> },
  ];
  const margens: Coluna<Linha>[] = [
    { chave: "titulo", titulo: "Título", mostrar: (l) => l.titulo, ordenar: (l) => l.titulo },
    { chave: "preco", titulo: "Preço", alinhar: "direita", mostrar: (l) => reaisDeCentavos(l.preco_centavos), ordenar: (l) => l.preco_centavos },
    { chave: "contribuicao", titulo: "Contribuição", alinhar: "direita", mostrar: (l) => reais(l.contribuicao) },
    { chave: "margem", titulo: "Margem", alinhar: "direita", mostrar: (l) => percentual(l.margem_pct) },
  ];
  type Historico = Resultado["historico"][number];
  const historico: Coluna<Historico>[] = [
    { chave: "titulo", titulo: "Título", mostrar: (h) => h.titulo, ordenar: (h) => h.titulo },
    { chave: "preco", titulo: "Preço", alinhar: "direita", mostrar: (h) => reaisDeCentavos(h.preco_centavos), ordenar: (h) => h.preco_centavos },
    { chave: "data", titulo: "Data", mostrar: (h) => dataBr(h.data), ordenar: (h) => h.data },
  ];

  return (
    <>
      {resultado.cotacao_antiga && <Aviso tipo="atencao">A cotação escolhida está antiga. Confirme o custo com o fornecedor.</Aviso>}
      <div className="grade-4">
        <Indicador rotulo="Anúncios analisados" valor={resultado.linhas.length} />
        <Indicador rotulo="Preço mediano" valor={resultado.mediana ? reais(resultado.mediana) : "Sem preços"} />
        <Indicador rotulo="Preço mínimo para o alvo" valor={resultado.preco_minimo ? reais(resultado.preco_minimo) : "Alvo inviável"}
          detalhe={`Margem-alvo da Calculadora: ${percentual(resultado.margem_alvo_pct)}. A compra exige pelo menos 20%.`} />
        <Indicador rotulo="Anúncios com margem no alvo" valor={resultado.no_alvo} />
      </div>
      <Caixa>
        <Abas rotulo="Resultados da pesquisa" abas={[
          { titulo: "Pesquisa", conteudo: <Tabela titulo="Anúncios" colunas={linhas} linhas={resultado.linhas} chaveLinha={(l) => l.id}
            vazio="Nenhum anúncio vinculado corresponde aos filtros. Cadastre ou importe e vincule anúncios a este produto." /> },
          { titulo: "Preços", conteudo: <Tabela titulo="Histórico de preços" colunas={historico} linhas={resultado.historico}
            chaveLinha={(h) => `${h.anuncio_id}-${h.data}-${h.preco_centavos}`} vazio="Sem preços observados." /> },
          { titulo: "Margens", conteudo: <Tabela titulo="Margem por anúncio" colunas={margens} linhas={resultado.linhas} chaveLinha={(l) => l.id}
            vazio="Sem anúncios para calcular margem." /> },
        ]} />
        <p className="legenda">
          Indicadores usam o preço mais recente de cada anúncio. Sinais não entram no cálculo; anúncio publicado não
          comprova demanda. Frete e despesas fixas não estão incluídos.
        </p>
      </Caixa>
    </>
  );
}

type DadosAnuncio = { marketplace: string; titulo: string; url: string; preco: string; data: string; produto_id: number | null; sinal: string };

function FormularioAnuncio({ produtos, produtoInicial, ocupado, aoEnviar }: {
  produtos: Opcao[];
  produtoInicial: number | null;
  ocupado: boolean;
  aoEnviar: (dados: DadosAnuncio) => Promise<unknown>;
}) {
  const [dados, setDados] = useState<DadosAnuncio>({
    marketplace: "", titulo: "", url: "", preco: "", data: hojeIso(), produto_id: produtoInicial, sinal: "" });
  const [erro, setErro] = useState<string | null>(null);
  const campo = (chave: keyof DadosAnuncio) => ({
    value: (dados[chave] ?? "") as string,
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
      <label>Marketplace<input required {...campo("marketplace")} /></label>
      <label>Título do anúncio<input required {...campo("titulo")} /></label>
      <label>URL do anúncio<input required type="url" {...campo("url")} /></label>
      <div className="campos-2">
        <label>Preço observado (R$)<input required inputMode="decimal" {...campo("preco")} /></label>
        <label>Data da observação<input type="date" required max={hojeIso()} {...campo("data")} /></label>
      </div>
      <label>Produto do anúncio
        <select value={dados.produto_id ?? ""} onChange={(e) => setDados({ ...dados, produto_id: e.target.value ? Number(e.target.value) : null })}>
          <option value="">Vincular depois</option>
          {produtos.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
        </select>
      </label>
      <label>Sinal observado, opcional<input {...campo("sinal")} placeholder="Ex.: mais vendido na categoria" /></label>
      <p className="legenda">Mesmo anúncio com preço novo vira mais um ponto no histórico; os anteriores são preservados.</p>
      <div><button type="submit" className="botao botao-principal" disabled={ocupado}>{ocupado ? "Salvando…" : "Salvar preço observado"}</button></div>
    </form>
  );
}

function FormularioVinculo({ anuncios, produtos, ocupado, aoEnviar }: {
  anuncios: AnuncioResumo[];
  produtos: Opcao[];
  ocupado: boolean;
  aoEnviar: (anuncioId: number, produtoId: number | null) => Promise<unknown>;
}) {
  // Anúncios sem vínculo primeiro: são os que mais pedem atenção.
  const ordenados = [...anuncios].sort((a, b) => Number(a.produto_id !== null) - Number(b.produto_id !== null));
  const [anuncioId, setAnuncioId] = useState(ordenados[0].id);
  const atual = anuncios.find((a) => a.id === anuncioId)!;
  const [produto, setProduto] = useState<number | null>(atual.produto_id);
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    try {
      await aoEnviar(anuncioId, produto);
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      <label>Anúncio para vincular
        <select value={anuncioId} onChange={(e) => {
          const novo = anuncios.find((a) => a.id === Number(e.target.value))!;
          setAnuncioId(novo.id);
          setProduto(novo.produto_id);
        }}>
          {ordenados.map((a) => (
            <option key={a.id} value={a.id}>{a.titulo} · {a.marketplace} · {a.produto ?? "sem vínculo"}</option>
          ))}
        </select>
      </label>
      <label>Vínculo do produto
        <select value={produto ?? ""} onChange={(e) => setProduto(e.target.value ? Number(e.target.value) : null)}>
          <option value="">Sem vínculo</option>
          {produtos.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
        </select>
      </label>
      <div><button type="submit" className="botao botao-principal" disabled={ocupado}>{ocupado ? "Salvando…" : "Salvar vínculo"}</button></div>
    </form>
  );
}
