// Cotações atuais com margem e preço mínimo já calculados pela API (radar/api/fornecedores.py).
import { dataBr, percentual, reais, reaisDeCentavos } from "../formato";
import { Aviso, Selo } from "./basicos";
import { BotaoExcluir } from "./Excluir";
import { Tabela, type Coluna } from "./Tabela";

export type LinhaSku = {
  id: number;
  codigo: string;
  produto_id: number;
  produto: string;
  fornecedor_id: number;
  fornecedor: string;
  custo_centavos: number;
  quantidade_minima: number;
  data_cotacao: string;
  cotacao_antiga: boolean;
  preco_venda_centavos: number | null;
  contribuicao: string | null;
  margem_pct: string | null;
  preco_minimo: string | null;
  aviso_preco_minimo: string | null;
};

// Ordenar por texto decimal exige comparar como número exato: inteiro de centésimos de milésimo.
const ordemDecimal = (texto: string | null) => {
  if (texto === null) return null;
  const [inteiro, fracao = ""] = texto.replace("-", "").split(".");
  const valor = BigInt(inteiro + (fracao + "000000").slice(0, 6));
  return texto.startsWith("-") ? -valor : valor;
};

const COLUNAS: Coluna<LinhaSku>[] = [
  { chave: "codigo", titulo: "Código", mostrar: (s) => s.codigo, ordenar: (s) => s.codigo },
  { chave: "produto", titulo: "Produto", mostrar: (s) => s.produto, ordenar: (s) => s.produto },
  { chave: "custo", titulo: "Custo", alinhar: "direita", mostrar: (s) => reaisDeCentavos(s.custo_centavos), ordenar: (s) => s.custo_centavos },
  { chave: "minima", titulo: "Qtd. mínima", alinhar: "direita", mostrar: (s) => s.quantidade_minima, ordenar: (s) => s.quantidade_minima },
  { chave: "data", titulo: "Cotação", ordenar: (s) => s.data_cotacao,
    mostrar: (s) => <>{dataBr(s.data_cotacao)}{s.cotacao_antiga && <> <Selo tom="amarelo">Antiga</Selo></>}</> },
  { chave: "preco", titulo: "Preço conservador", alinhar: "direita", ordenar: (s) => s.preco_venda_centavos,
    mostrar: (s) => (s.preco_venda_centavos === null ? "Não informado" : reaisDeCentavos(s.preco_venda_centavos)) },
  { chave: "contribuicao", titulo: "Contribuição", alinhar: "direita", ordenar: (s) => ordemDecimal(s.contribuicao),
    mostrar: (s) => (s.contribuicao === null ? "Sem estimativa" : reais(s.contribuicao)) },
  { chave: "margem", titulo: "Margem estimada", alinhar: "direita", ordenar: (s) => ordemDecimal(s.margem_pct),
    mostrar: (s) => (s.margem_pct === null ? "Sem estimativa" : percentual(s.margem_pct)) },
  { chave: "minimo", titulo: "Preço mínimo p/ alvo", alinhar: "direita", ordenar: (s) => ordemDecimal(s.preco_minimo),
    mostrar: (s) => (s.preco_minimo === null ? "Alvo inviável" : reais(s.preco_minimo)) },
];

export function TabelaSkus({ skus, limiteDias, semFornecedor, excluir }: {
  skus: LinhaSku[];
  limiteDias: number;
  semFornecedor?: boolean;
  /** Quando informado, cada linha ganha "Excluir SKU" (apaga todas as cotações do código, se não estiver em uso). */
  excluir?: { ocupado: boolean; aoExcluir: (sku: LinhaSku) => Promise<unknown> };
}) {
  const colunas = semFornecedor ? [...COLUNAS] : [
    ...COLUNAS.slice(0, 2),
    { chave: "fornecedor", titulo: "Fornecedor", mostrar: (s: LinhaSku) => s.fornecedor, ordenar: (s: LinhaSku) => s.fornecedor },
    ...COLUNAS.slice(2),
  ];
  if (excluir) colunas.push({ chave: "excluir", titulo: "Excluir", mostrar: (s: LinhaSku) => (
    <BotaoExcluir rotulo="Excluir SKU" pergunta={`Excluir o SKU ${s.codigo} e todas as cotações dele?`}
      ocupado={excluir.ocupado} aoConfirmar={() => excluir.aoExcluir(s)} />
  ) });
  const aviso = skus.find((s) => s.aviso_preco_minimo)?.aviso_preco_minimo;
  return (
    <div className="pilha">
      <Tabela titulo="Cotações atuais" colunas={colunas} linhas={skus} chaveLinha={(s) => s.id} vazio="Nenhuma cotação cadastrada." />
      {skus.some((s) => s.cotacao_antiga) && (
        <Aviso tipo="atencao">Há cotações com mais de {limiteDias} dias. Confirme os valores com o fornecedor.</Aviso>
      )}
      {aviso && <Aviso tipo="atencao">{aviso}</Aviso>}
      <p className="legenda">Exibida a cotação mais recente de cada código por fornecedor. As anteriores são preservadas.
        {excluir && " Só é possível excluir um SKU que não esteja em kit, plano de compra ou cenário de margem."}</p>
    </div>
  );
}
