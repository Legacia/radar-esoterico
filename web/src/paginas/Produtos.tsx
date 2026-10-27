// Produtos e SKUs: catálogo dos candidatos e cotações de cada fornecedor, sempre com a data.
// Margens e preço mínimo das cotações vêm prontos da API.
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { pedir } from "../api";
import { Abas } from "../componentes/Abas";
import { Aviso, Painel as Caixa, Selo } from "../componentes/basicos";
import { useFicha } from "../componentes/ficha";
import { Gaveta } from "../componentes/Gaveta";
import { mensagemDeErro, useGravacao, type Executar } from "../componentes/gravacao";
import { useNotificar } from "../componentes/Notificacoes";
import { Tabela, type Coluna } from "../componentes/Tabela";
import { TabelaSkus, type LinhaSku } from "../componentes/TabelaSkus";
import { hojeIso } from "../formato";
import { enderecoDe, useRota } from "../rotas";

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
type FichaProduto = Produto & { limite_cotacao_dias: number; skus: LinhaSku[] };
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
            { titulo: `Cotações (${ficha.skus.length})`, conteudo: <TabelaSkus skus={ficha.skus} limiteDias={ficha.limite_cotacao_dias} /> },
            { titulo: "Registrar cotação", conteudo: (
              <FormularioCotacao key={versao} fornecedores={fornecedores} ocupado={bloqueado}
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
        <label>Nome do produto<input required value={dados.nome} onChange={(e) => setDados({ ...dados, nome: e.target.value })} /></label>
        <label>Família<input value={dados.familia} onChange={(e) => setDados({ ...dados, familia: e.target.value })} /></label>
        <label>Status do produto<input required value={dados.status} onChange={(e) => setDados({ ...dados, status: e.target.value })} /></label>
      </div>
      <fieldset className="grupo">
        <legend>Avaliação do produto</legend>
        {CONFERENCIAS.map(([campo, , rotulo]) => {
          const chave = campo as keyof DadosProduto;
          return (
            <label key={campo} className="tarefa">
              <input type="checkbox" checked={dados[chave] as boolean} onChange={(e) => setDados({ ...dados, [chave]: e.target.checked })} />
              {rotulo}
            </label>
          );
        })}
      </fieldset>
      <div><button type="submit" className="botao botao-principal" disabled={ocupado}>{ocupado ? "Salvando…" : "Salvar produto"}</button></div>
    </form>
  );
}

type DadosCotacao = { fornecedor_id: number; codigo: string; custo: string; quantidade_minima: number; data: string; preco_venda: string | null };

function FormularioCotacao({ fornecedores, ocupado, aoEnviar }: {
  fornecedores: FornecedorOpcao[];
  ocupado: boolean;
  aoEnviar: (dados: DadosCotacao) => Promise<unknown>;
}) {
  const [fornecedor, setFornecedor] = useState(fornecedores[0]?.id ?? 0);
  const [codigo, setCodigo] = useState("");
  const [custo, setCusto] = useState("");
  const [quantidade, setQuantidade] = useState("1");
  const [data, setData] = useState(hojeIso());
  const [preco, setPreco] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  if (!fornecedores.length) {
    return <Aviso>Cadastre um fornecedor na tela <a href={enderecoDe("fornecedores")}>Fornecedores</a> para lançar uma cotação.</Aviso>;
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    // Quantidade é um inteiro de unidades, não dinheiro; o servidor confere de novo.
    if (!/^\d{1,9}$/.test(quantidade.trim())) {
      setErro("A quantidade mínima deve ser um inteiro maior que zero.");
      return;
    }
    try {
      await aoEnviar({ fornecedor_id: fornecedor, codigo, custo, quantidade_minima: Number.parseInt(quantidade, 10),
                       data, preco_venda: preco.trim() || null });
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      <p className="legenda">
        Repita o código e informe a nova data para recotar um SKU. O preço de venda é a estimativa conservadora de vocês,
        ainda sem pesquisa de mercado automática.
      </p>
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      <div className="campos-2">
        <label>Fornecedor da cotação
          <select value={fornecedor} onChange={(e) => setFornecedor(Number(e.target.value))}>
            {fornecedores.map((f) => <option key={f.id} value={f.id}>{f.nome}</option>)}
          </select>
        </label>
        <label>Código no fornecedor<input required value={codigo} onChange={(e) => setCodigo(e.target.value)} /></label>
        <label>Custo unitário (R$)<input required inputMode="decimal" value={custo} onChange={(e) => setCusto(e.target.value)} /></label>
        <label>Quantidade mínima<input required inputMode="numeric" value={quantidade} onChange={(e) => setQuantidade(e.target.value)} /></label>
        <label>Data da cotação<input type="date" required max={hojeIso()} value={data} onChange={(e) => setData(e.target.value)} /></label>
        <label>Preço conservador de venda (R$), opcional<input inputMode="decimal" value={preco} onChange={(e) => setPreco(e.target.value)} /></label>
      </div>
      <div><button type="submit" className="botao botao-principal" disabled={ocupado}>{ocupado ? "Salvando…" : "Salvar cotação"}</button></div>
    </form>
  );
}
