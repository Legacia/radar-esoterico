// Cotações atuais com margem e preço mínimo já calculados pela API (radar/api/fornecedores.py).
import { dataBr, percentual, reais, reaisDeCentavos } from "../formato";
import { Aviso, Selo } from "./basicos";
import { BotaoExcluir } from "./Excluir";
import { Tabela, type Coluna } from "./Tabela";

export type LinhaSku = {
  id: number;
  /** Código interno da variação (RAD-000001), o SKU de vocês. */
  codigo: string;
  codigo_parceiro: string;
  variacao_id: number;
  cor: string;
  tamanho: string;
  unidade_venda: string;
  preco_cotado_centavos: number;
  unidades_por_cotacao: number;
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

/** "Preto · G · caixa": cor e tamanho quando existem, e a unidade de venda. */
export const descreverVariacao = (v: { cor: string; tamanho: string; unidade_venda: string }) =>
  [v.cor, v.tamanho, v.unidade_venda].filter((t) => t.trim()).join(" · ");

/** Exclusão de um SKU: fornecedor e código interno vão junto para a API conferir que é o SKU confirmado na tela. */
export const caminhoExcluirSku = (sku: LinhaSku) =>
  `/cotacoes/${sku.id}?${new URLSearchParams({ fornecedor_id: String(sku.fornecedor_id), codigo: sku.codigo })}`;

// Ordenar por texto decimal exige comparar como número exato: inteiro de centésimos de milésimo.
const ordemDecimal = (texto: string | null) => {
  if (texto === null) return null;
  const [inteiro, fracao = ""] = texto.replace("-", "").split(".");
  const valor = BigInt(inteiro + (fracao + "000000").slice(0, 6));
  return texto.startsWith("-") ? -valor : valor;
};

const COLUNAS: Coluna<LinhaSku>[] = [
  { chave: "codigo", titulo: "SKU", mostrar: (s) => s.codigo, ordenar: (s) => s.codigo },
  { chave: "produto", titulo: "Produto", ordenar: (s) => s.produto,
    mostrar: (s) => <>{s.produto}<div className="legenda-inline">{descreverVariacao(s)}</div></> },
  { chave: "parceiro", titulo: "Cód. parceiro", mostrar: (s) => s.codigo_parceiro || "—", ordenar: (s) => s.codigo_parceiro },
  { chave: "custo", titulo: "Custo por unidade de venda", alinhar: "direita", ordenar: (s) => s.custo_centavos,
    mostrar: (s) => <>{reaisDeCentavos(s.custo_centavos)}{s.unidades_por_cotacao > 1 && (
      <div className="legenda-inline">{reaisDeCentavos(s.preco_cotado_centavos)} ÷ {s.unidades_por_cotacao}</div>)}</> },
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
    <BotaoExcluir rotulo="Excluir SKU" pergunta={`Excluir as cotações do SKU ${s.codigo} neste fornecedor?`}
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
      <p className="legenda">Exibida a cotação mais recente de cada SKU por fornecedor; as anteriores são preservadas.
        Custo, quantidade mínima e preço conservador estão na unidade de venda do SKU.
        {excluir && " Só é possível excluir um SKU que não esteja em kit, plano de compra ou cenário de margem."}</p>
    </div>
  );
}
