import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Pesquisa, type Resultado } from "../src/paginas/Pesquisa";
import { ProvedorNotificacoes } from "../src/componentes/Notificacoes";
import { hojeIso } from "../src/formato";

const BASE = {
  anuncios: [
    { id: 1, marketplace: "loja fictícia", titulo: "Kit fictício 3 incensos", url: "https://example.invalid/1", produto_id: 1, produto: "Kit fictício" },
    { id: 2, marketplace: "loja fictícia", titulo: "Anúncio sem vínculo", url: "https://example.invalid/2", produto_id: null, produto: null },
  ],
  produtos: [{ id: 1, nome: "Kit fictício" }, { id: 2, nome: "Cristal fictício" }],
};
const COTACOES = [
  { id: 10, fornecedor: "Fornecedor fictício", codigo: "KIT-01", data_cotacao: "2026-10-20", custo_centavos: 2000 },
  { id: 11, fornecedor: "Fornecedor fictício", codigo: "KIT-02", data_cotacao: "2026-08-01", custo_centavos: 1800 },
];
const RESULTADO: Resultado = {
  linhas: [{ id: 1, marketplace: "loja fictícia", titulo: "Kit fictício 3 incensos", url: "https://example.invalid/1",
    sinal: "Mais vendido", preco_centavos: 5990, data: "2026-10-25", contribuicao: "14.33", margem_pct: "0.2392320534223706176961602671" }],
  historico: [{ anuncio_id: 1, titulo: "Kit fictício 3 incensos", preco_centavos: 5990, data: "2026-10-25" },
              { anuncio_id: 1, titulo: "Kit fictício 3 incensos", preco_centavos: 6490, data: "2026-10-01" }],
  mediana: "59.9", preco_minimo: "55.56", no_alvo: 1, margem_alvo_pct: "0.20", custo_centavos: 2000,
  data_cotacao: "2026-10-20", cotacao_antiga: false, marketplaces: ["loja fictícia", "outra loja"],
};

type Chamada = { caminho: string; metodo: string; corpo: unknown };

function simular(extra: (c: Chamada) => unknown = () => undefined) {
  const chamadas: Chamada[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (entrada, init) => {
    const c = { caminho: String(entrada), metodo: init?.method ?? "GET", corpo: init?.body ? JSON.parse(String(init.body)) : undefined };
    chamadas.push(c);
    const especial = await extra(c);
    const corpo = especial !== undefined ? especial
      : c.caminho === "/api/pesquisa/anuncios" && c.metodo === "GET" ? BASE
      : c.caminho.startsWith("/api/pesquisa/cotacoes") ? (c.caminho.endsWith("produto_id=2") ? [] : COTACOES)
      : c.caminho.startsWith("/api/pesquisa?") ? RESULTADO
      : { anuncio_id: 3, novo_preco: true, ok: true };
    return new Response(JSON.stringify(corpo), { status: 200 });
  });
  return chamadas;
}

const consultas = (chamadas: Chamada[]) => chamadas.filter((c) => c.caminho.startsWith("/api/pesquisa?"))
  .map((c) => Object.fromEntries(new URLSearchParams(c.caminho.split("?")[1])));

const mostrar = (hash = "#/pesquisa") => {
  window.location.hash = hash;
  return render(<ProvedorNotificacoes><Pesquisa /></ProvedorNotificacoes>);
};

describe("Pesquisa de oportunidades", () => {
  it("usa a cotação mais recente e mostra o que a API calculou", async () => {
    const chamadas = simular();
    mostrar();
    expect(await screen.findByText("Anúncios analisados")).toBeInTheDocument();
    expect(consultas(chamadas).at(-1)).toEqual({ produto_id: "1", cotacao_id: "10", marketplace: "", termo: "" });
    expect(screen.getByText("Preço mediano").nextSibling).toHaveTextContent("R$ 59,90");
    expect(screen.getByText("Preço mínimo para o alvo").nextSibling).toHaveTextContent("R$ 55,56");
    expect(screen.getByText(/Margem-alvo da Calculadora: 20,0%/)).toBeInTheDocument();
    const linha = screen.getByRole("cell", { name: "Kit fictício 3 incensos" }).closest("tr")!;
    expect(within(linha).getByRole("link", { name: "Abrir anúncio" })).toHaveAttribute("rel", "noopener noreferrer");
    expect(linha).toHaveTextContent("Mais vendido");
    await userEvent.click(screen.getByRole("tab", { name: "Margens" }));
    expect(screen.getByRole("cell", { name: "R$ 14,33" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "23,9%" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Preços" }));
    expect(screen.getByRole("cell", { name: "R$ 64,90" })).toBeInTheDocument();
  });

  it("filtros vão para o endereço e para a consulta", async () => {
    const chamadas = simular();
    mostrar();
    await screen.findByText("Anúncios analisados");
    await userEvent.selectOptions(screen.getByLabelText("Cotação usada como custo"), "11");
    await waitFor(() => expect(consultas(chamadas).at(-1)?.cotacao_id).toBe("11"));
    expect(window.location.hash).toBe("#/pesquisa?produto=1&cotacao=11");
    await userEvent.selectOptions(screen.getByLabelText("Filtrar marketplace"), "outra loja");
    await waitFor(() => expect(consultas(chamadas).at(-1)?.marketplace).toBe("outra loja"));
    await userEvent.type(screen.getByLabelText("Buscar no título dos anúncios"), "incenso");
    await userEvent.click(screen.getByRole("button", { name: "Buscar" }));
    await waitFor(() => expect(consultas(chamadas).at(-1)).toEqual({ produto_id: "1", cotacao_id: "11", marketplace: "outra loja", termo: "incenso" }));
  });

  it("cotação antiga e produto sem cotação têm aviso", async () => {
    simular((c) => c.caminho.startsWith("/api/pesquisa?") ? { ...RESULTADO, cotacao_antiga: true } : undefined);
    mostrar();
    expect(await screen.findByText(/cotação escolhida está antiga/)).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Produto pesquisado"), "2");
    expect(await screen.findByText(/Registre uma cotação desse produto/)).toBeInTheDocument();
    expect(screen.queryByText("Anúncios analisados")).toBeNull();
  });

  it("resposta antiga que chega por último é descartada", async () => {
    const liberar: (() => void)[] = [];
    simular(async (c) => {
      if (!c.caminho.startsWith("/api/pesquisa?")) return undefined;
      if (c.caminho.includes("cotacao_id=10")) {
        await new Promise<void>((r) => liberar.push(r));
        return { ...RESULTADO, mediana: "10" };
      }
      return { ...RESULTADO, mediana: "99" };
    });
    mostrar();
    await userEvent.selectOptions(await screen.findByLabelText("Cotação usada como custo"), "11");
    expect(await screen.findByText("R$ 99,00")).toBeInTheDocument();
    liberar.forEach((r) => r());
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.getByText("Preço mediano").nextSibling).toHaveTextContent("R$ 99,00");
  });

  it("consulta nova que falha não deixa à vista o resultado da cotação anterior", async () => {
    simular((c) => c.caminho.includes("cotacao_id=11") ? Promise.resolve(undefined).then(() => { throw new TypeError("rede"); }) : undefined);
    mostrar();
    expect(await screen.findByText("Anúncios analisados")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Cotação usada como custo"), "11");
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.queryByText("Anúncios analisados")).toBeNull();
    expect(screen.queryByText("Preço mínimo para o alvo")).toBeNull();
  });

  it("voltar no navegador devolve o termo da busca ao campo", async () => {
    const chamadas = simular();
    mostrar("#/pesquisa?produto=1&termo=incenso");
    expect(await screen.findByLabelText("Buscar no título dos anúncios")).toHaveValue("incenso");
    window.location.hash = "#/pesquisa?produto=1&termo=cristal";
    await waitFor(() => expect(screen.getByLabelText("Buscar no título dos anúncios")).toHaveValue("cristal"));
    window.location.hash = "#/pesquisa?produto=1&termo=incenso";
    await waitFor(() => expect(screen.getByLabelText("Buscar no título dos anúncios")).toHaveValue("incenso"));
    await waitFor(() => expect(consultas(chamadas).at(-1)?.termo).toBe("incenso"));
  });

  it("cadastra anúncio uma vez só, com o produto pesquisado já escolhido", async () => {
    const chamadas = simular();
    mostrar();
    await userEvent.click(await screen.findByRole("button", { name: "Cadastrar anúncio ou preço" }));
    const gaveta = screen.getByRole("dialog", { name: "Cadastrar anúncio ou novo preço observado" });
    await userEvent.type(within(gaveta).getByLabelText("Marketplace"), "Loja fictícia");
    await userEvent.type(within(gaveta).getByLabelText("Título do anúncio"), "Kit fictício");
    await userEvent.type(within(gaveta).getByLabelText("URL do anúncio"), "https://example.invalid/3");
    await userEvent.type(within(gaveta).getByLabelText("Preço observado (R$)"), "49,90");
    const formulario = within(gaveta).getByRole("button", { name: "Salvar preço observado" }).closest("form")!;
    fireEvent.submit(formulario);
    fireEvent.submit(formulario);
    expect(await screen.findByText("Observação registrada.")).toBeInTheDocument();
    const posts = chamadas.filter((c) => c.metodo === "POST");
    expect(posts).toHaveLength(1);
    expect(posts[0].corpo).toEqual({ marketplace: "Loja fictícia", titulo: "Kit fictício", url: "https://example.invalid/3",
      preco: "49,90", data: hojeIso(), produto_id: 1, sinal: "" });
  });

  it("preço repetido avisa que nada foi duplicado; erro fica no formulário", async () => {
    let tentativa = 0;
    simular((c) => {
      if (c.metodo !== "POST") return undefined;
      return ++tentativa === 1 ? { anuncio_id: 1, novo_preco: false } : undefined;
    });
    mostrar();
    await userEvent.click(await screen.findByRole("button", { name: "Cadastrar anúncio ou preço" }));
    let gaveta = screen.getByRole("dialog", { name: "Cadastrar anúncio ou novo preço observado" });
    for (const [rotulo, valor] of [["Marketplace", "x"], ["Título do anúncio", "x"], ["URL do anúncio", "https://example.invalid/1"], ["Preço observado (R$)", "59,90"]]) {
      await userEvent.type(within(gaveta).getByLabelText(rotulo), valor);
    }
    await userEvent.click(within(gaveta).getByRole("button", { name: "Salvar preço observado" }));
    expect(await screen.findByText(/nada foi duplicado/)).toBeInTheDocument();

    vi.spyOn(globalThis, "fetch").mockImplementation(async (_e, init) => init?.method === "POST"
      ? new Response(JSON.stringify({ detail: "A URL deve usar http ou https e ter um endereço válido, sem credenciais." }), { status: 400 })
      : new Response(JSON.stringify(BASE), { status: 200 }));
    await userEvent.click(screen.getByRole("button", { name: "Cadastrar anúncio ou preço" }));
    gaveta = screen.getByRole("dialog", { name: "Cadastrar anúncio ou novo preço observado" });
    for (const [rotulo, valor] of [["Marketplace", "x"], ["Título do anúncio", "x"], ["URL do anúncio", "http://a.b"], ["Preço observado (R$)", "1"]]) {
      await userEvent.type(within(gaveta).getByLabelText(rotulo), valor);
    }
    await userEvent.click(within(gaveta).getByRole("button", { name: "Salvar preço observado" }));
    expect(await within(gaveta).findByRole("alert")).toHaveTextContent("http ou https");
    expect(within(gaveta).getByLabelText("Marketplace")).toHaveValue("x");
  });

  it("vincula anúncio, começando pelos sem vínculo", async () => {
    const chamadas = simular();
    mostrar();
    await userEvent.click(await screen.findByRole("button", { name: "Vincular anúncio a produto (1 sem vínculo)" }));
    const gaveta = screen.getByRole("dialog", { name: "Vincular ou corrigir produto de um anúncio" });
    expect(within(gaveta).getByLabelText("Anúncio para vincular")).toHaveValue("2");
    expect(within(gaveta).getByLabelText("Vínculo do produto")).toHaveValue("");
    await userEvent.selectOptions(within(gaveta).getByLabelText("Vínculo do produto"), "2");
    await userEvent.click(within(gaveta).getByRole("button", { name: "Salvar vínculo" }));
    await waitFor(() => expect(chamadas.some((c) => c.metodo === "PUT")).toBe(true));
    expect(chamadas.find((c) => c.metodo === "PUT")).toMatchObject({ caminho: "/api/pesquisa/anuncios/2/produto", corpo: { produto_id: 2 } });
  });
});
