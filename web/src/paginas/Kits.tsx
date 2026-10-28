// Kits: composição por produto, custo pela cotação de cada componente e estoque por componente.
// Custos e necessidade conjunta vêm prontos da API; o planejamento não baixa nem reserva estoque.
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { pedir } from "../api";
import { Aviso, Indicador, Painel as Caixa, Selo } from "../componentes/basicos";
import { EmbalagemApoio, type Apoio } from "../componentes/EmbalagemApoio";
import { useFicha } from "../componentes/ficha";
import { Gaveta } from "../componentes/Gaveta";
import { mensagemDeErro, useGravacao, type Executar } from "../componentes/gravacao";
import { useNotificar } from "../componentes/Notificacoes";
import { Tabela, type Coluna } from "../componentes/Tabela";
import { dataBr, percentual, reais, reaisDeCentavos, textoDeCentavos } from "../formato";
import { enderecoDe, useRota } from "../rotas";
import { Dica } from "../componentes/Dica";

type KitResumo = { id: number; nome: string; quantidade_planejada: number };
type ProdutoEstoque = { id: number; nome: string; estoque_atual: number };
type Necessidade = { produto: string; necessario: number; estoque: number; falta: number };
type Base = { kits: KitResumo[]; produtos: ProdutoEstoque[]; necessidade: Necessidade[] };
type Componente = {
  produto_id: number; produto: string; quantidade: number; estoque_atual: number;
  custo_unitario_centavos: number | null; codigo: string | null; data_cotacao: string | null; sku_fornecedor_id: number | null;
};
type MargemKit = {
  embalagem: string; embalagem_propria: boolean; contribuicao: string | null; margem_pct: string | null;
  preco_minimo: string | null; aviso_preco_minimo: string | null;
};
export type FichaKit = KitResumo & {
  componentes: Componente[]; custo_unitario: string | null; custo_lote: string | null;
  preco_venda_centavos: number | null; apoio: Apoio; margem: MargemKit;
};
type Cotacao = { id: number; fornecedor: string; codigo: string; data_cotacao: string; custo_centavos: number };

// Quantidades são inteiros de unidades, não dinheiro; o servidor confere de novo.
const inteiro = (texto: string, minimo: number) => (/^\d{1,9}$/.test(texto.trim()) && Number(texto) >= minimo ? Number(texto) : null);

export function Kits() {
  const { filtros } = useRota();
  const [base, setBase] = useState<Base | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [criando, setCriando] = useState(false);
  const gravacao = useGravacao();
  const notificar = useNotificar();

  // Cada lista nova gera uma versão: o formulário de componente é recriado também quando o estoque
  // dos produtos chega, não só quando chega a ficha do kit (as duas consultas correm em paralelo).
  const [versaoBase, setVersaoBase] = useState(0);
  const carregar = useCallback(() => pedir<Base>("/kits").then(
    (d) => { setBase(d); setVersaoBase((v) => v + 1); setErro(null); }, (e) => setErro(mensagemDeErro(e))), []);
  useEffect(() => { carregar(); }, [carregar]);

  if (erro) return <Aviso tipo="erro">{erro}</Aviso>;
  if (!base) return <p className="legenda">Carregando kits…</p>;

  const kitId = base.kits.some((k) => String(k.id) === filtros.kit) ? Number(filtros.kit) : base.kits[0]?.id;
  const escolher = (id: number) => { window.location.hash = enderecoDe("kits", { kit: String(id) }); };

  const colunasNecessidade: Coluna<Necessidade>[] = [
    { chave: "produto", titulo: "Produto", mostrar: (n) => n.produto, ordenar: (n) => n.produto },
    { chave: "necessario", titulo: "Necessário", alinhar: "direita", mostrar: (n) => n.necessario, ordenar: (n) => n.necessario },
    { chave: "estoque", titulo: "Estoque físico", alinhar: "direita", mostrar: (n) => n.estoque, ordenar: (n) => n.estoque },
    { chave: "falta", titulo: "Falta", alinhar: "direita", ordenar: (n) => n.falta,
      mostrar: (n) => (n.falta ? <Selo tom="laranja">{n.falta}</Selo> : <Selo tom="verde">0</Selo>) },
  ];

  return (
    <>
      <div className="cabecalho-acoes">
        <button type="button" className="botao botao-principal" disabled={gravacao.ocupado} onClick={() => setCriando(true)}>Criar kit</button>
        {base.kits.length > 0 && (
          <label className="em-linha"><span className="rotulo">Kit<Dica de="Kit" /></span>
            <select value={kitId} onChange={(e) => escolher(Number(e.target.value))}>
              {base.kits.map((k) => <option key={k.id} value={k.id}>{k.nome} · {k.quantidade_planejada} planejados</option>)}
            </select>
          </label>
        )}
      </div>

      {kitId === undefined ? (
        <Aviso>Crie um kit para compor seus produtos.</Aviso>
      ) : (
        <DetalheKit key={kitId} id={kitId} produtos={base.produtos} versaoBase={versaoBase} executar={gravacao.executar} ocupado={gravacao.ocupado}
          gravacoes={gravacao.concluidas} aoMudar={carregar} />
      )}

      <Caixa titulo="Necessidade conjunta dos kits planejados">
        <Tabela titulo="Necessidade conjunta" colunas={colunasNecessidade} linhas={base.necessidade} chaveLinha={(n) => n.produto}
          vazio="Nenhum kit com quantidade planejada." />
        <p className="legenda">
          O estoque é compartilhado por componente. Este planejamento não baixa nem reserva estoque e não entra
          automaticamente no orçamento. Planeje a compra de componentes na <a href={enderecoDe("compras")}>Decisão de compra</a>.
        </p>
      </Caixa>

      <Gaveta aberta={criando} titulo="Criar kit" aoFechar={() => setCriando(false)}>
        <FormularioNome ocupado={gravacao.ocupado} aoEnviar={(nome) => gravacao.executar(async () => {
          const { id } = await pedir<{ id: number }>("/kits", { corpo: { nome } });
          setCriando(false);
          notificar("Kit criado.");
          await carregar();
          escolher(id);
        })} />
      </Gaveta>
    </>
  );
}

function FormularioNome({ ocupado, aoEnviar }: { ocupado: boolean; aoEnviar: (nome: string) => Promise<unknown> }) {
  const [nome, setNome] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    try { await aoEnviar(nome); } catch (e) { setErro(mensagemDeErro(e)); }
  }
  return (
    <form className="formulario" onSubmit={enviar}>
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      <label><span className="rotulo">Nome do novo kit<Dica de="Nome do novo kit" /></span><input required value={nome} onChange={(e) => setNome(e.target.value)} /></label>
      <div><button type="submit" className="botao botao-principal" disabled={ocupado}>{ocupado ? "Salvando…" : "Criar kit"}</button></div>
    </form>
  );
}

function DetalheKit({ id, produtos, versaoBase, executar, ocupado, gravacoes, aoMudar }: {
  id: number;
  versaoBase: number;
  produtos: ProdutoEstoque[];
  executar: Executar;
  ocupado: boolean;
  gravacoes: number;
  aoMudar: () => Promise<void>;
}) {
  const { ficha: kit, erro, versao, bloqueado, gravar } = useFicha<FichaKit>({
    caminho: `/kits/${id}`, id, executar, ocupado, gravacoes, aoMudar });
  // Componente escolhido fica aqui fora: o formulário é recriado a cada recarga, mas não volta ao primeiro.
  const [componente, setComponente] = useState<number | undefined>(produtos[0]?.id);

  if (erro) return <Aviso tipo="erro">{erro}</Aviso>;
  if (!kit) return <p className="legenda">Carregando kit…</p>;

  const colunas: Coluna<Componente>[] = [
    { chave: "produto", titulo: "Produto", mostrar: (c) => c.produto, ordenar: (c) => c.produto },
    { chave: "quantidade", titulo: "Unidades por kit", alinhar: "direita", mostrar: (c) => c.quantidade, ordenar: (c) => c.quantidade },
    { chave: "estoque", titulo: "Estoque físico", alinhar: "direita", mostrar: (c) => c.estoque_atual, ordenar: (c) => c.estoque_atual },
    { chave: "custo", titulo: "Custo unitário", alinhar: "direita", ordenar: (c) => c.custo_unitario_centavos,
      mostrar: (c) => (c.custo_unitario_centavos === null ? <Selo tom="laranja">Sem cotação</Selo> : reaisDeCentavos(c.custo_unitario_centavos)) },
    { chave: "cotacao", titulo: "Cotação", mostrar: (c) => (c.codigo && c.data_cotacao ? `${c.codigo} · ${dataBr(c.data_cotacao)}` : "—") },
    { chave: "remover", titulo: "Ação", mostrar: (c) => (
      <button type="button" className="botao-discreto link" disabled={bloqueado} aria-label={`Remover ${c.produto} do kit`}
        onClick={() => gravar(() => pedir(`/kits/${id}/componentes/${c.produto_id}`, { metodo: "DELETE" }), "Componente removido.")
          .catch(() => {})}>
        Remover
      </button>
    ) },
  ];

  return (
    <div className="grade-2">
      <Caixa titulo="Composição e custo">
        {kit.custo_unitario ? (
          <div className="grade-2 grade-igual">
            <Indicador rotulo="Custo de um kit" valor={reais(kit.custo_unitario)} />
            {kit.custo_lote && <Indicador rotulo={`Custo dos ${kit.quantidade_planejada} kits planejados`} valor={reais(kit.custo_lote)} />}
          </div>
        ) : (
          <Aviso>Complete a composição e a cotação de cada componente para calcular o custo.</Aviso>
        )}
        <div className="resultado">
          <Tabela titulo="Componentes do kit" colunas={colunas} linhas={kit.componentes} chaveLinha={(c) => c.produto_id}
            vazio="Kit ainda sem componentes." />
        </div>
      </Caixa>
      <Caixa titulo="Margem do kit">
        <MargemDoKit kit={kit} />
      </Caixa>
      <Caixa titulo="Embalagem do kit">
        <p className="legenda">O kit usa só a própria embalagem: os itens de apoio dos componentes não entram aqui.</p>
        <EmbalagemApoio apoio={kit.apoio} padrao={kit.margem.embalagem} caminho={`/kits/${id}/apoio`}
          quem="do kit" ocupado={bloqueado} gravar={gravar} />
      </Caixa>
      <div className="pilha">
        <Caixa titulo="Plano do kit">
          <FormularioPlano key={versao} kit={kit} ocupado={bloqueado}
            aoEnviar={(dados) => gravar(() => pedir(`/kits/${id}`, { metodo: "PUT", corpo: dados }), "Plano do kit salvo.")} />
        </Caixa>
        <Caixa titulo="Adicionar ou atualizar componente">
          <FormularioComponente key={`${versao}-${versaoBase}`} produtos={produtos} ocupado={bloqueado}
            produtoInicial={componente} aoEscolher={setComponente}
            aoSalvar={(produtoId, dados) => gravar(() => pedir(`/kits/${id}/componentes/${produtoId}`, { metodo: "PUT", corpo: dados }), "Componente salvo.")}
            aoAjustarEstoque={(produtoId, estoque) => gravar(() => pedir(`/estoque/${produtoId}`, { metodo: "PUT", corpo: { estoque } }), "Estoque atualizado por produto.")} />
        </Caixa>
      </div>
    </div>
  );
}

function MargemDoKit({ kit }: { kit: FichaKit }) {
  const m = kit.margem;
  if (!kit.custo_unitario) return <Aviso>Complete o custo dos componentes para calcular a margem.</Aviso>;
  return (
    <div className="pilha">
      <div className="grade-2 grade-igual">
        {m.contribuicao && m.margem_pct ? (
          <Indicador rotulo="Contribuição por kit" valor={reais(m.contribuicao)} detalhe={`Margem de ${percentual(m.margem_pct)}`}
            tom={m.contribuicao.startsWith("-") ? "vermelho" : undefined} />
        ) : (
          <Indicador rotulo="Contribuição por kit" valor="—" detalhe="Informe o preço conservador no plano do kit" />
        )}
        <Indicador rotulo="Preço mínimo para a margem-alvo" valor={m.preco_minimo ? reais(m.preco_minimo) : "—"} />
      </div>
      {m.aviso_preco_minimo && <Aviso tipo="atencao">{m.aviso_preco_minimo}</Aviso>}
      <p className="legenda">
        Custo dos componentes {reais(kit.custo_unitario)} e embalagem {reais(m.embalagem)}
        {m.embalagem_propria ? " (itens de apoio do kit)" : " (padrão da configuração)"}. Frete e despesas fixas não entram.
      </p>
    </div>
  );
}

function FormularioPlano({ kit, ocupado, aoEnviar }: {
  kit: FichaKit;
  ocupado: boolean;
  aoEnviar: (dados: { nome: string; quantidade_planejada: number; preco_venda: string }) => Promise<unknown>;
}) {
  const [nome, setNome] = useState(kit.nome);
  const [quantidade, setQuantidade] = useState(String(kit.quantidade_planejada));
  const [preco, setPreco] = useState(kit.preco_venda_centavos ? textoDeCentavos(kit.preco_venda_centavos) : "");
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    const numero = inteiro(quantidade, 0);
    if (numero === null) return setErro("A quantidade planejada deve ser um inteiro não negativo.");
    try { await aoEnviar({ nome, quantidade_planejada: numero, preco_venda: preco.trim() }); } catch (e) { setErro(mensagemDeErro(e)); }
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      <div className="campos-2">
        <label><span className="rotulo">Nome do kit<Dica de="Nome do kit" /></span><input required value={nome} onChange={(e) => setNome(e.target.value)} /></label>
        <label><span className="rotulo">Kits planejados<Dica de="Kits planejados" /></span><input required inputMode="numeric" value={quantidade} onChange={(e) => setQuantidade(e.target.value)} /></label>
        <label><span className="rotulo">Preço conservador de venda do kit (R$), opcional<Dica de="Preço conservador de venda do kit (R$), opcional" /></span>
          <input inputMode="decimal" value={preco} onChange={(e) => setPreco(e.target.value)} />
        </label>
      </div>
      <p className="legenda">Zero retira o kit da necessidade conjunta.</p>
      <div><button type="submit" className="botao botao-principal" disabled={ocupado}>{ocupado ? "Salvando…" : "Salvar plano do kit"}</button></div>
    </form>
  );
}

function FormularioComponente({ produtos, produtoInicial, aoEscolher, ocupado, aoSalvar, aoAjustarEstoque }: {
  produtos: ProdutoEstoque[];
  produtoInicial: number | undefined;
  aoEscolher: (id: number) => void;
  ocupado: boolean;
  aoSalvar: (produtoId: number, dados: { quantidade: number; cotacao_id: number }) => Promise<unknown>;
  aoAjustarEstoque: (produtoId: number, estoque: number) => Promise<unknown>;
}) {
  const [produtoId, setProdutoId] = useState(produtos.some((p) => p.id === produtoInicial) ? produtoInicial : produtos[0]?.id);
  const [cotacoes, setCotacoes] = useState<Cotacao[] | null>(null);
  const [cotacaoId, setCotacaoId] = useState<number | null>(null);
  const [quantidade, setQuantidade] = useState("1");
  const produto = produtos.find((p) => p.id === produtoId);
  const [estoque, setEstoque] = useState(String(produto?.estoque_atual ?? 0));
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (produtoId === undefined) return;
    let valido = true;
    setCotacoes(null);
    pedir<Cotacao[]>(`/pesquisa/cotacoes?produto_id=${produtoId}`).then((lista) => {
      // Ignora a resposta se a pessoa já escolheu outro componente.
      if (!valido) return;
      setCotacoes(lista);
      setCotacaoId(lista[0]?.id ?? null);
    }, (e) => { if (valido) setErro(mensagemDeErro(e)); });
    return () => { valido = false; };
  }, [produtoId]);

  if (!produtos.length || produtoId === undefined) {
    return <Aviso>Cadastre produtos em <a href={enderecoDe("produtos")}>Produtos e SKUs</a> para compor o kit.</Aviso>;
  }

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    const numero = inteiro(quantidade, 1);
    if (numero === null) return setErro("A quantidade do componente deve ser um inteiro positivo.");
    if (cotacaoId === null) return;
    try { await aoSalvar(produtoId!, { quantidade: numero, cotacao_id: cotacaoId }); } catch (e) { setErro(mensagemDeErro(e)); }
  }

  async function ajustar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    const numero = inteiro(estoque, 0);
    if (numero === null) return setErro("O estoque deve ser um inteiro não negativo.");
    try { await aoAjustarEstoque(produtoId!, numero); } catch (e) { setErro(mensagemDeErro(e)); }
  }

  return (
    <div className="pilha">
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      <label className="formulario"><span className="rotulo">Componente<Dica de="Componente" /></span>
        <select value={produtoId} onChange={(e) => {
          const novo = produtos.find((p) => p.id === Number(e.target.value))!;
          setProdutoId(novo.id);
          aoEscolher(novo.id);
          setEstoque(String(novo.estoque_atual));
        }}>
          {produtos.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
        </select>
      </label>
      {cotacoes === null ? <p className="legenda">Carregando cotações…</p> : !cotacoes.length ? (
        <Aviso>Cadastre uma cotação para este componente em <a href={enderecoDe("produtos")}>Produtos e SKUs</a>.</Aviso>
      ) : (
        <form className="formulario" onSubmit={salvar}>
          <div className="campos-2">
            <label><span className="rotulo">Cotação de custo do componente<Dica de="Cotação de custo do componente" /></span>
              <select value={cotacaoId ?? ""} onChange={(e) => setCotacaoId(Number(e.target.value))}>
                {cotacoes.map((c) => (
                  <option key={c.id} value={c.id}>{c.fornecedor} · {c.codigo} · {dataBr(c.data_cotacao)} · {reaisDeCentavos(c.custo_centavos)}</option>
                ))}
              </select>
            </label>
            <label><span className="rotulo">Unidades desse componente por kit<Dica de="Unidades desse componente por kit" /></span>
              <input required inputMode="numeric" value={quantidade} onChange={(e) => setQuantidade(e.target.value)} />
            </label>
          </div>
          <div><button type="submit" className="botao botao-principal" disabled={ocupado}>{ocupado ? "Salvando…" : "Salvar componente"}</button></div>
        </form>
      )}
      <form className="formulario grupo" onSubmit={ajustar}>
        <label><span className="rotulo">Estoque físico atual do componente<Dica de="Estoque físico atual do componente" /></span>
          <input required inputMode="numeric" value={estoque} onChange={(e) => setEstoque(e.target.value)} />
        </label>
        <div><button type="submit" className="botao" disabled={ocupado}>Atualizar estoque físico</button></div>
      </form>
    </div>
  );
}
