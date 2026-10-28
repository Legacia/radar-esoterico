// Navegação pelo endereço: #/pagina?filtro=valor. Assim cada tela e filtro tem um link próprio
// e a API só precisa servir um index.html.
import { useEffect, useState } from "react";

export type Pagina = { chave: string; titulo: string; descricao: string };
export type Secao = { titulo: string; paginas: Pagina[] };

export const SECOES: Secao[] = [
  { titulo: "Visão geral", paginas: [
    { chave: "painel", titulo: "Painel", descricao: "Indicadores, plano de 30 dias e pendências." },
    { chave: "contas", titulo: "Contas", descricao: "Quem pode entrar no Radar e troca de senha." },
  ] },
  { titulo: "Fornecimento", paginas: [
    { chave: "fornecedores", titulo: "Fornecedores", descricao: "Ciclo, ficha, cotações e checklist de promoção." },
    { chave: "produtos", titulo: "Produtos e SKUs", descricao: "Catálogo de candidatos e cotações." },
    { chave: "kits", titulo: "Kits", descricao: "Composição e estoque por componente." },
  ] },
  { titulo: "Mercado", paginas: [
    { chave: "pesquisa", titulo: "Pesquisa de oportunidades", descricao: "Anúncios, preços e margens por anúncio." },
    { chave: "importar", titulo: "Importar CSV", descricao: "Entrada de anúncios e preços observados." },
  ] },
  { titulo: "Decisão", paginas: [
    { chave: "calculadora", titulo: "Calculadora e parâmetros", descricao: "Margem por venda e preço mínimo." },
    { chave: "compras", titulo: "Decisão de compra", descricao: "Orçamento, critérios e quantidades." },
  ] },
];

export const PAGINAS = SECOES.flatMap((secao) => secao.paginas);
export const INICIAL = "painel";

export type Rota = { pagina: string; filtros: Record<string, string> };

export function lerRota(hash: string): Rota {
  const [caminho, busca = ""] = hash.replace(/^#\/?/, "").split("?");
  const pagina = PAGINAS.some((p) => p.chave === caminho) ? caminho : INICIAL;
  return { pagina, filtros: Object.fromEntries(new URLSearchParams(busca)) };
}

export function enderecoDe(pagina: string, filtros: Record<string, string> = {}): string {
  const busca = new URLSearchParams(Object.entries(filtros).filter(([, v]) => v !== "")).toString();
  return `#/${pagina}${busca ? "?" + busca : ""}`;
}

export function useRota(): Rota {
  const [rota, setRota] = useState(() => lerRota(window.location.hash));
  useEffect(() => {
    const mudar = () => setRota(lerRota(window.location.hash));
    window.addEventListener("hashchange", mudar);
    return () => window.removeEventListener("hashchange", mudar);
  }, []);
  return rota;
}
