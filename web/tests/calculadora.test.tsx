import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Calculadora, type Configuracao } from "../src/paginas/Calculadora";
import { ProvedorNotificacoes } from "../src/componentes/Notificacoes";

const CONFIG: Configuracao = {
  parametros: { comissao_pct: "0.20", tributo_pct: "0.06", margem_alvo_pct: "0.20", tarifa_fixa: "4.5", embalagem: "2.5", outros: "3" },
  campos: { comissao: "20,00", tributo: "6,00", margem_alvo: "20,00", tarifa_fixa: "4,5", embalagem: "2,5", outros: "3" },
  limite_cotacao_dias: 15,
};
const CASO = { contribuicao: "14.33", margem_pct: "0.2392320534223706176961602671", preco_minimo: "55.56", aviso_preco_minimo: null };

type Chamada = { caminho: string; metodo: string; corpo: unknown };

function simular(resposta: (chamada: Chamada) => { status?: number; corpo: unknown } | Promise<{ status?: number; corpo: unknown }>) {
  const chamadas: Chamada[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (entrada, init) => {
    const chamada = { caminho: String(entrada), metodo: init?.method ?? "GET", corpo: init?.body ? JSON.parse(String(init.body)) : undefined };
    chamadas.push(chamada);
    const r = await resposta(chamada);
    return new Response(JSON.stringify(r.corpo), { status: r.status ?? 200 });
  });
  return chamadas;
}

const padrao = (c: Chamada) => ({ corpo: c.caminho === "/api/configuracao" ? CONFIG : CASO });
const mostrar = () => render(<ProvedorNotificacoes><Calculadora /></ProvedorNotificacoes>);

async function preencherVenda(preco: string, custo: string) {
  const caixa = (await screen.findByRole("region", { name: "Simular uma venda" }));
  await userEvent.type(within(caixa).getByLabelText("Preço de venda (R$)"), preco);
  await userEvent.type(within(caixa).getByLabelText("Custo do produto (R$)"), custo);
  await userEvent.click(within(caixa).getByRole("button", { name: "Calcular margem" }));
  return caixa;
}

describe("Calculadora", () => {
  it("mostra o caso obrigatório como a API calculou: R$ 14,33, 23,9% e R$ 55,56", async () => {
    const chamadas = simular(padrao);
    mostrar();
    const caixa = await preencherVenda("59,90", "20,00");
    expect(await within(caixa).findByText("R$ 14,33")).toBeInTheDocument();
    expect(within(caixa).getByText("23,9%")).toBeInTheDocument();
    expect(within(caixa).getByText("R$ 55,56")).toBeInTheDocument();
    expect(chamadas.find((c) => c.caminho === "/api/calculadora/simular")!.corpo).toEqual({ preco: "59,90", custo: "20,00" });
  });

  it("explica entrada inválida e preço mínimo inviável", async () => {
    simular((c) => c.caminho === "/api/configuracao" ? { corpo: CONFIG }
      : (c.corpo as { preco: string }).preco === "abc"
        ? { status: 400, corpo: { detail: "Informe um número, por exemplo 20,00 ou 1.234,56." } }
        : { corpo: { ...CASO, contribuicao: "-5.68", preco_minimo: null, aviso_preco_minimo: "Não existe preço mínimo com esses percentuais." } });
    mostrar();
    const caixa = await preencherVenda("abc", "1");
    expect(await within(caixa).findByRole("alert")).toHaveTextContent("Informe um número");
    await userEvent.clear(within(caixa).getByLabelText("Preço de venda (R$)"));
    await userEvent.type(within(caixa).getByLabelText("Preço de venda (R$)"), "18");
    await userEvent.click(within(caixa).getByRole("button", { name: "Calcular margem" }));
    expect(await within(caixa).findByText("-R$ 5,68")).toBeInTheDocument();
    expect(within(caixa).getByText("Inviável")).toBeInTheDocument();
    expect(within(caixa).getByText("Não existe preço mínimo com esses percentuais.")).toBeInTheDocument();
    expect(within(caixa).queryByRole("alert")).toBeNull();
  });

  it("resposta antiga da simulação que chega por último é descartada", async () => {
    const liberar: (() => void)[] = [];
    simular(async (c) => {
      if (c.caminho === "/api/configuracao") return { corpo: CONFIG };
      const preco = (c.corpo as { preco: string }).preco;
      if (preco === "10") await new Promise<void>((r) => liberar.push(r));
      return { corpo: { ...CASO, contribuicao: preco === "10" ? "1.00" : "14.33" } };
    });
    mostrar();
    const caixa = await preencherVenda("10", "1");
    await userEvent.clear(within(caixa).getByLabelText("Preço de venda (R$)"));
    await userEvent.type(within(caixa).getByLabelText("Preço de venda (R$)"), "59,90");
    await userEvent.click(within(caixa).getByRole("button", { name: "Calcular margem" }));
    expect(await within(caixa).findByText("R$ 14,33")).toBeInTheDocument();
    liberar.forEach((r) => r());
    await new Promise((r) => setTimeout(r, 50));
    expect(within(caixa).getByText("R$ 14,33")).toBeInTheDocument();
    expect(within(caixa).queryByText("R$ 1,00")).toBeNull();
  });

  it("salva parâmetros uma vez só e refaz a simulação com os valores novos", async () => {
    let salvo = false;
    const chamadas = simular((c) => {
      if (c.metodo === "PUT") { salvo = true; return { corpo: CONFIG }; }
      if (c.caminho === "/api/configuracao") return { corpo: salvo ? { ...CONFIG, campos: { ...CONFIG.campos, comissao: "14,50" } } : CONFIG };
      return { corpo: { ...CASO, contribuicao: salvo ? "17.62" : "14.33" } };
    });
    mostrar();
    const venda = await preencherVenda("59,90", "20,00");
    expect(await within(venda).findByText("R$ 14,33")).toBeInTheDocument();
    const parametros = screen.getByRole("region", { name: "Parâmetros" });
    expect(within(parametros).getByLabelText("Comissão (%)")).toHaveValue("20,00");
    await userEvent.clear(within(parametros).getByLabelText("Comissão (%)"));
    await userEvent.type(within(parametros).getByLabelText("Comissão (%)"), "14,50");
    const formulario = within(parametros).getByRole("button", { name: "Salvar parâmetros" }).closest("form")!;
    fireEvent.submit(formulario);
    fireEvent.submit(formulario);
    expect(await within(venda).findByText("R$ 17,62")).toBeInTheDocument();
    const puts = chamadas.filter((c) => c.metodo === "PUT");
    expect(puts).toHaveLength(1);
    expect(puts[0].corpo).toEqual({ ...CONFIG.campos, comissao: "14,50", limite_cotacao_dias: 15 });
    expect(await screen.findByText(/Parâmetros salvos/)).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "Parâmetros" })).getByLabelText("Comissão (%)")).toHaveValue("14,50");
  });

  it("erro ao salvar parâmetros mantém o que foi digitado", async () => {
    simular((c) => c.metodo === "PUT"
      ? { status: 400, corpo: { detail: "Valores em reais devem ter no máximo duas casas decimais." } }
      : padrao(c));
    mostrar();
    const parametros = await screen.findByRole("region", { name: "Parâmetros" });
    await userEvent.clear(within(parametros).getByLabelText("Tarifa fixa (R$)"));
    await userEvent.type(within(parametros).getByLabelText("Tarifa fixa (R$)"), "4,555");
    await userEvent.click(within(parametros).getByRole("button", { name: "Salvar parâmetros" }));
    expect(await within(parametros).findByRole("alert")).toHaveTextContent("duas casas");
    expect(within(parametros).getByLabelText("Tarifa fixa (R$)")).toHaveValue("4,555");
  });

  it("dias que não são inteiro são recusados antes de enviar", async () => {
    const chamadas = simular(padrao);
    mostrar();
    const parametros = await screen.findByRole("region", { name: "Parâmetros" });
    await userEvent.clear(within(parametros).getByLabelText("Cotação antiga após quantos dias?"));
    await userEvent.type(within(parametros).getByLabelText("Cotação antiga após quantos dias?"), "15,5");
    await userEvent.click(within(parametros).getByRole("button", { name: "Salvar parâmetros" }));
    expect(await within(parametros).findByRole("alert")).toHaveTextContent("entre 1 e 3650 dias");
    await waitFor(() => expect(chamadas.some((c) => c.metodo === "PUT")).toBe(false));
  });
});
