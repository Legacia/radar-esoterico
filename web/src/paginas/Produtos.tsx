// Produtos e SKUs: catálogo dos candidatos e cotações de cada fornecedor, sempre com a data.
// Margens e preço mínimo das cotações vêm prontos da API.
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { pedir } from "../api";
import { Abas } from "../componentes/Abas";
import { Aviso, Painel as Caixa, Selo } from "../componentes/basicos";
import { EmbalagemApoio, type Apoio } from "../componentes/EmbalagemApoio";
import { useFicha } from "../componentes/ficha";
import { Gaveta } from "../componentes/Gaveta";
import { mensagemDeErro, useGravacao, type Executar } from "../componentes/gravacao";
import { useNotificar } from "../componentes/Notificacoes";
import { Tabela, type Coluna } from "../componentes/Tabela";
import { TabelaSkus, caminhoExcluirSku, descreverVariacao, type LinhaSku } from "../componentes/TabelaSkus";
import { BotaoExcluir } from "../componentes/Excluir";
import { hojeIso } from "../formato";
import { enderecoDe, useRota } from "../rotas";
import { Dica } from "../componentes/Dica";
import type { ChaveDica } from "../dicas";

export type Produto = {
  id: number;
  nome: string;
  familia: string | null;
  status: string;
  especificacoes_conferidas: number;
  procedencia_conferida: number;
  qualidade_conferida: number;
  validado: number;
  estoque_atual: number;
};
export type Variacao = { id: number; codigo: string; cor: string; tamanho: string; unidade_venda: string; cotacoes: number };
type FichaProduto = Produto & { limite_cotacao_dias: number; skus: LinhaSku[]; variacoes: Variacao[]; apoio: Apoio; embalagem_padrao: string };
type FornecedorOpcao = { id: number; nome: string };

const CONFERENCIAS: [keyof Produto, string, string][] = [
  ["especificacoes_conferidas", "Especificações", "Especificações conferidas"],
  ["procedencia_conferida", "Procedência", "Procedência conferida"],
  ["qualidade_conferida", "Qualidade", "Qualidade conferida pela Anna"],
];
const conferidas = (p: Produto) => CONFERENCIAS.filter(([campo]) => p[campo]).length;

export function Produtos() {
  const { filtros } = useRota();
  const [produtos, setProdutos] = useState<Produto[] | null>(null);
  const [fornecedores, setFornecedores] = useState<FornecedorOpcao[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [cadastrando, setCadastrando] = useState(false);
  const gravacao = useGravacao();
  const notificar = useNotificar();
  const fichaId = Number(filtros.ficha) || null;

  const carregar = useCallback(() => pedir<{ produtos: Produto[]; fornecedores: FornecedorOpcao[] }>("/produtos").then(
    (d) => { setProdutos(d.produtos); setFornecedores(d.fornecedores); setErro(null); },
    (e) => setErro(mensagemDeErro(e)),
  ), []);
  useEffect(() => { carregar(); }, [carregar]);

  const abrir = (id: number | null) => { window.location.hash = enderecoDe("produtos", { ficha: id ? String(id) : "" }); };

  if (erro) return <Aviso tipo="erro">{erro}</Aviso>;
  if (!produtos) return <p className="legenda">Carregando produtos…</p>;

  const colunas: Coluna<Produto>[] = [
    { chave: "nome", titulo: "Produto", mostrar: (p) => p.nome, ordenar: (p) => p.nome },
    { chave: "familia", titulo: "Família", ordenar: (p) => p.familia || null,
      mostrar: (p) => p.familia || <span className="legenda-inline">Não informada</span> },
    { chave: "status", titulo: "Status", mostrar: (p) => p.status, ordenar: (p) => p.status },
    { chave: "conferencias", titulo: "Conferências", alinhar: "direita", ordenar: conferidas,
      mostrar: (p) => <Selo tom={conferidas(p) === 3 ? "verde" : "laranja"}>{conferidas(p)} de 3</Selo> },
    { chave: "validado", titulo: "Validado para compra", ordenar: (p) => p.validado,
      mostrar: (p) => (p.validado ? <Selo tom="verde">Sim</Selo> : <Selo>Não</Selo>) },
    { chave: "estoque", titulo: "Estoque físico", alinhar: "direita", mostrar: (p) => p.estoque_atual, ordenar: (p) => p.estoque_atual },
  ];

  return (
    <>
      <div className="cabecalho-acoes">
        <button type="button" className="botao botao-principal" disabled={gravacao.ocupado} onClick={() => setCadastrando(true)}>
          Cadastrar produto
        </button>
      </div>
      <Caixa titulo="Catálogo de candidatos">
        <Tabela titulo="Produtos" colunas={colunas} linhas={produtos} chaveLinha={(p) => p.id}
          vazio='Nenhum produto cadastrado. Use "Cadastrar produto" para começar.' aoClicar={(p) => abrir(p.id)} />
        <p className="legenda">
          Clique num produto para ver as cotações, registrar uma nova ou editar a avaliação. A validação para
          compra e o estoque são definidos na Decisão de compra e em Kits.
        </p>
      </Caixa>

      <Gaveta aberta={cadastrando} titulo="Cadastrar produto" aoFechar={() => setCadastrando(false)}>
        <FormularioProduto ocupado={gravacao.ocupado} aoEnviar={(dados) => gravacao.executar(async () => {
          const { id } = await pedir<{ id: number }>("/produtos", { corpo: dados });
          setCadastrando(false);
          notificar("Produto salvo.");
          await carregar();
          abrir(id);
        })} />
      </Gaveta>

      {fichaId !== null && (
        // A chave recria a ficha ao trocar de produto: nada da ficha anterior é reaproveitado.
        <FichaProduto key={fichaId} id={fichaId} fornecedores={fornecedores} executar={gravacao.executar}
          ocupado={gravacao.ocupado} gravacoes={gravacao.concluidas} aoMudar={carregar} aoFechar={() => abrir(null)} />
      )}
    </>
  );
}

function FichaProduto({ id, fornecedores, executar, ocupado, gravacoes, aoMudar, aoFechar }: {
  id: number;
  fornecedores: FornecedorOpcao[];
  executar: Executar;
  ocupado: boolean;
  gravacoes: number;
  aoMudar: () => Promise<void>;
  aoFechar: () => void;
}) {
  const { ficha, erro, versao, bloqueado, gravar } = useFicha<FichaProduto>({
    caminho: `/produtos/${id}`, id, executar, ocupado, gravacoes, aoMudar });

  return (
    <Gaveta aberta larga titulo={ficha?.nome ?? "Ficha do produto"} aoFechar={aoFechar}>
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      {!ficha && !erro && <p className="legenda">Carregando ficha…</p>}
      {ficha && (
        <div className="pilha">
          <ul className="selos">
            <li><Selo tom="azul">{ficha.status}</Selo></li>
            <li><Selo>{ficha.familia || "Família não informada"}</Selo></li>
            {CONFERENCIAS.map(([campo, curto]) => (
              <li key={campo}>
                <Selo tom={ficha[campo] ? "verde" : "laranja"}>
                  <span aria-hidden="true">{ficha[campo] ? "✓ " : "○ "}</span>{curto}
                  <span className="so-leitor">{ficha[campo] ? ": conferida" : ": pendente"}</span>
                </Selo>
              </li>
            ))}
          </ul>
          <Abas rotulo="Partes da ficha" abas={[
            { titulo: `Cotações (${ficha.skus.length})`, conteudo: (
              <TabelaSkus skus={ficha.skus} limiteDias={ficha.limite_cotacao_dias} excluir={{ ocupado: bloqueado,
                aoExcluir: (sku) => gravar(() => pedir(caminhoExcluirSku(sku), { metodo: "DELETE" }), `SKU ${sku.codigo} excluído.`) }} />
            ) },
            { titulo: `Variações (${ficha.variacoes.length})`, conteudo: (
              <Variacoes key={versao} produtoId={id} variacoes={ficha.variacoes} ocupado={bloqueado} gravar={gravar} />
            ) },
            { titulo: "Embalagem e apoio", conteudo: (
              <EmbalagemApoio apoio={ficha.apoio} padrao={ficha.embalagem_padrao} caminho={`/produtos/${id}/apoio`}
                quem="do produto" ocupado={bloqueado} gravar={gravar} />
            ) },
            { titulo: "Registrar cotação", conteudo: (
              <FormularioCotacao key={versao} fornecedores={fornecedores} variacoes={ficha.variacoes} ocupado={bloqueado}
                aoEnviar={(dados) => gravar(() => pedir(`/produtos/${id}/cotacoes`, { corpo: dados }), "Cotação registrada.")} />
            ) },
            { titulo: "Editar produto e avaliação", conteudo: (
              <FormularioProduto key={versao} produto={ficha} ocupado={bloqueado}
                aoEnviar={(dados) => gravar(() => pedir(`/produtos/${id}`, { metodo: "PUT", corpo: dados }), "Produto salvo.")} />
            ) },
          ]} />
        </div>
      )}
    </Gaveta>
  );
}

type DadosProduto = {
  nome: string; familia: string; status: string;
  especificacoes_conferidas: boolean; procedencia_conferida: boolean; qualidade_conferida: boolean;
};

function FormularioProduto({ produto, ocupado, aoEnviar }: {
  produto?: Produto;
  ocupado: boolean;
  aoEnviar: (dados: DadosProduto) => Promise<unknown>;
}) {
  const [dados, setDados] = useState<DadosProduto>(() => ({
    nome: produto?.nome ?? "", familia: produto?.familia ?? "", status: produto?.status ?? "Candidato",
    especificacoes_conferidas: !!produto?.especificacoes_conferidas,
    procedencia_conferida: !!produto?.procedencia_conferida,
    qualidade_conferida: !!produto?.qualidade_conferida,
  }));
  const [erro, setErro] = useState<string | null>(null);

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
        <label><span className="rotulo">Nome do produto<Dica de="Nome do produto" /></span><input required value={dados.nome} onChange={(e) => setDados({ ...dados, nome: e.target.value })} /></label>
        <label><span className="rotulo">Família<Dica de="Família" /></span><input value={dados.familia} onChange={(e) => setDados({ ...dados, familia: e.target.value })} /></label>
        <label><span className="rotulo">Status do produto<Dica de="Status do produto" /></span><input required value={dados.status} onChange={(e) => setDados({ ...dados, status: e.target.value })} /></label>
      </div>
      <fieldset className="grupo">
        <legend>Avaliação do produto<Dica de="Avaliação do produto" /></legend>
        {CONFERENCIAS.map(([campo, , rotulo]) => {
          const chave = campo as keyof DadosProduto;
          return (
            <label key={campo} className="tarefa">
              <input type="checkbox" checked={dados[chave] as boolean} onChange={(e) => setDados({ ...dados, [chave]: e.target.checked })} />
              {rotulo}<Dica de={rotulo as ChaveDica} />
            </label>
          );
        })}
      </fieldset>
      <div><button type="submit" className="botao botao-principal" disabled={ocupado}>{ocupado ? "Salvando…" : "Salvar produto"}</button></div>
    </form>
  );
}

type DadosVariacao = { cor: string; tamanho: string; unidade_venda: string };

function Variacoes({ produtoId, variacoes, ocupado, gravar }: {
  produtoId: number;
  variacoes: Variacao[];
  ocupado: boolean;
  gravar: (acao: () => Promise<unknown>, sucesso: string) => Promise<unknown>;
}) {
  // null: nova variação; número: editando aquela variação.
  const [editando, setEditando] = useState<number | null>(null);
  const atual = variacoes.find((v) => v.id === editando);
  return (
    <div className="pilha">
      <Tabela titulo="Variações do produto" linhas={variacoes} chaveLinha={(v) => v.id} colunas={[
        { chave: "codigo", titulo: "SKU", mostrar: (v) => v.codigo, ordenar: (v) => v.codigo },
        { chave: "cor", titulo: "Cor", mostrar: (v) => v.cor || "—", ordenar: (v) => v.cor },
        { chave: "tamanho", titulo: "Tamanho", mostrar: (v) => v.tamanho || "—", ordenar: (v) => v.tamanho },
        { chave: "unidade", titulo: "Unidade de venda", mostrar: (v) => v.unidade_venda, ordenar: (v) => v.unidade_venda },
        { chave: "cotacoes", titulo: "Cotações", alinhar: "direita", mostrar: (v) => v.cotacoes, ordenar: (v) => v.cotacoes },
        { chave: "acoes", titulo: "Ações", mostrar: (v) => (
          <div className="pilha">
            <div><button type="button" className="botao-discreto link" disabled={ocupado} onClick={() => setEditando(v.id)}
              aria-label={`Editar ${v.codigo}`}>Editar</button></div>
            <BotaoExcluir rotulo="Excluir" pergunta={`Excluir a variação ${v.codigo}?`} ocupado={ocupado}
              aoConfirmar={() => gravar(() => pedir(`/variacoes/${v.id}?${new URLSearchParams({ codigo: v.codigo })}`, { metodo: "DELETE" }),
                `Variação ${v.codigo} excluída.`)} />
          </div>
        ) },
      ]} />
      <p className="legenda">
        Cada variação é um SKU de vocês, com código gerado pelo Radar. Custo e preço de venda são sempre por
        unidade de venda (por exemplo: o caldeirão é vendido por unidade; o incenso, pela caixa).
      </p>
      <FormularioVariacao key={editando ?? "nova"} variacao={atual} ocupado={ocupado}
        aoCancelar={atual ? () => setEditando(null) : undefined}
        aoEnviar={(dados) => gravar(
          () => pedir(atual ? `/produtos/${produtoId}/variacoes/${atual.id}` : `/produtos/${produtoId}/variacoes`,
            { metodo: atual ? "PUT" : "POST", corpo: dados }),
          atual ? `Variação ${atual.codigo} salva.` : "Variação criada.")} />
    </div>
  );
}

function FormularioVariacao({ variacao, ocupado, aoEnviar, aoCancelar }: {
  variacao?: Variacao;
  ocupado: boolean;
  aoEnviar: (dados: DadosVariacao) => Promise<unknown>;
  aoCancelar?: () => void;
}) {
  const [cor, setCor] = useState(variacao?.cor ?? "");
  const [tamanho, setTamanho] = useState(variacao?.tamanho ?? "");
  const [unidade, setUnidade] = useState(variacao?.unidade_venda ?? "unidade");
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    try { await aoEnviar({ cor, tamanho, unidade_venda: unidade }); } catch (e) { setErro(mensagemDeErro(e)); }
  }

  return (
    <form className="formulario grupo" onSubmit={enviar}>
      <h3 className="subtitulo">{variacao ? `Editar ${variacao.codigo}` : "Nova variação"}</h3>
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      <div className="campos-3">
        <label><span className="rotulo">Cor<Dica de="Cor" /></span><input value={cor} onChange={(e) => setCor(e.target.value)} /></label>
        <label><span className="rotulo">Tamanho<Dica de="Tamanho" /></span><input value={tamanho} onChange={(e) => setTamanho(e.target.value)} /></label>
        <label><span className="rotulo">Unidade de venda mínima<Dica de="Unidade de venda mínima" /></span>
          <input required value={unidade} onChange={(e) => setUnidade(e.target.value)} placeholder="unidade, caixa com 8 varetas…" />
        </label>
      </div>
      <div>
        <button type="submit" className="botao botao-principal" disabled={ocupado}>
          {ocupado ? "Salvando…" : variacao ? "Salvar variação" : "Criar variação"}
        </button>
        {aoCancelar && <> <button type="button" className="botao" onClick={aoCancelar}>Cancelar</button></>}
      </div>
    </form>
  );
}

type DadosCotacao = {
  fornecedor_id: number; variacao_id: number; codigo: string; custo: string; unidades_por_cotacao: number;
  quantidade_minima: number; data: string; preco_venda: string | null;
};

// Quantidades são inteiros de unidades, não dinheiro; o servidor confere de novo.
const inteiroPositivo = (texto: string) => (/^\d{1,9}$/.test(texto.trim()) && Number(texto) >= 1 ? Number.parseInt(texto, 10) : null);

function FormularioCotacao({ fornecedores, variacoes, ocupado, aoEnviar }: {
  fornecedores: FornecedorOpcao[];
  variacoes: Variacao[];
  ocupado: boolean;
  aoEnviar: (dados: DadosCotacao) => Promise<unknown>;
}) {
  const [fornecedor, setFornecedor] = useState(fornecedores[0]?.id ?? 0);
  const [variacao, setVariacao] = useState(variacoes[0]?.id ?? 0);
  const [codigo, setCodigo] = useState("");
  const [custo, setCusto] = useState("");
  const [unidades, setUnidades] = useState("1");
  const [quantidade, setQuantidade] = useState("1");
  const [data, setData] = useState(hojeIso());
  const [preco, setPreco] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  if (!fornecedores.length) {
    return <Aviso>Cadastre um fornecedor na tela <a href={enderecoDe("fornecedores")}>Fornecedores</a> para lançar uma cotação.</Aviso>;
  }
  if (!variacoes.length) return <Aviso>Crie uma variação na aba Variações para lançar uma cotação.</Aviso>;
  const unidadeVenda = variacoes.find((v) => v.id === variacao)?.unidade_venda ?? "unidade";

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    const minima = inteiroPositivo(quantidade);
    if (minima === null) return setErro("A quantidade mínima deve ser um inteiro maior que zero.");
    const porCotacao = inteiroPositivo(unidades);
    if (porCotacao === null) return setErro("As unidades de venda por unidade cotada devem ser um inteiro maior que zero.");
    try {
      await aoEnviar({ fornecedor_id: fornecedor, variacao_id: variacao, codigo, custo, unidades_por_cotacao: porCotacao,
                       quantidade_minima: minima, data, preco_venda: preco.trim() || null });
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      <p className="legenda">
        Informe o preço como o fornecedor cota (unidade, caixa, pacote…) e quantas unidades de venda ({unidadeVenda})
        vêm nessa unidade cotada. O Radar calcula o custo por unidade de venda, que é o usado na margem.
        Repita a variação e informe a nova data para recotar.
      </p>
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      <div className="campos-2">
        <label><span className="rotulo">Fornecedor da cotação<Dica de="Fornecedor da cotação" /></span>
          <select value={fornecedor} onChange={(e) => setFornecedor(Number(e.target.value))}>
            {fornecedores.map((f) => <option key={f.id} value={f.id}>{f.nome}</option>)}
          </select>
        </label>
        <label><span className="rotulo">Variação (SKU)<Dica de="Variação (SKU)" /></span>
          <select value={variacao} onChange={(e) => setVariacao(Number(e.target.value))}>
            {variacoes.map((v) => <option key={v.id} value={v.id}>{v.codigo} · {descreverVariacao(v)}</option>)}
          </select>
        </label>
        <label><span className="rotulo">Código do parceiro (opcional)<Dica de="Código do parceiro (opcional)" /></span>
          <input value={codigo} onChange={(e) => setCodigo(e.target.value)} />
        </label>
        <label><span className="rotulo">Preço cotado (R$)<Dica de="Preço cotado (R$)" /></span>
          <input required inputMode="decimal" value={custo} onChange={(e) => setCusto(e.target.value)} />
        </label>
        <label><span className="rotulo">Unidades de venda na unidade cotada<Dica de="Unidades de venda na unidade cotada" /></span>
          <input required inputMode="numeric" value={unidades} onChange={(e) => setUnidades(e.target.value)} />
        </label>
        <label><span className="rotulo">Quantidade mínima (em unidades cotadas)<Dica de="Quantidade mínima (em unidades cotadas)" /></span>
          <input required inputMode="numeric" value={quantidade} onChange={(e) => setQuantidade(e.target.value)} />
        </label>
        <label><span className="rotulo">Data da cotação<Dica de="Data da cotação" /></span>
          <input type="date" required max={hojeIso()} value={data} onChange={(e) => setData(e.target.value)} />
        </label>
        <label><span className="rotulo">Preço conservador por unidade de venda (R$), opcional<Dica de="Preço conservador por unidade de venda (R$), opcional" /></span>
          <input inputMode="decimal" value={preco} onChange={(e) => setPreco(e.target.value)} />
        </label>
      </div>
      <div><button type="submit" className="botao botao-principal" disabled={ocupado}>{ocupado ? "Salvando…" : "Salvar cotação"}</button></div>
    </form>
  );
}
