import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Fornecedores, type Ficha } from "../src/paginas/Fornecedores";
import { ProvedorNotificacoes } from "../src/componentes/Notificacoes";

const LISTA = {
  etapas: ["Descoberto", "Descartado ou pausado"],
  fornecedores: [{ id: 1, nome: "Fornecedor fictício Alfa", status: "Descoberto", prazo: "", condicao_pagamento: "", data_ultima_cotacao: null }],
};
const FICHA: Ficha = {
  ...LISTA.fornecedores[0], cnpj: "", contato: "", pedido_minimo_centavos: 0, data_oficial: null, motivo_descarte: null,
  cnpj_verificado: 0, condicoes_verificadas: 0, emite_nota: 0, amostra_avaliada: 0, reposicao_confirmada: 0,
  checklist: [], margem_minima_pct: "0.20", limite_cotacao_dias: 15,
  skus: [{
    id: 5, codigo: "KIT-01", produto_id: 3, produto: "Kit fictício", fornecedor_id: 1, fornecedor: "Fornecedor fictício Alfa",
    custo_centavos: 2000, quantidade_minima: 10, data_cotacao: "2026-10-20", cotacao_antiga: false,
    preco_venda_centavos: null, contribuicao: null, margem_pct: null, preco_minimo: "55.56", aviso_preco_minimo: null,
  }],
  contatos: [],
};

type Chamada = { caminho: string; metodo: string };

function simular(respostas: Record<string, { status: number; corpo: unknown }>) {
  const chamadas: Chamada[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (entrada, init) => {
    const caminho = String(entrada);
    const metodo = init?.method ?? "GET";
    chamadas.push({ caminho, metodo });
    const r = respostas[`${metodo} ${caminho}`]
      ?? { status: 200, corpo: caminho === "/api/fornecedores" ? LISTA : FICHA };
    return new Response(JSON.stringify(r.corpo), { status: r.status });
  });
  return chamadas;
}

async function abrirFicha() {
  window.location.hash = "#/fornecedores?ficha=1";
  render(<ProvedorNotificacoes><Fornecedores /></ProvedorNotificacoes>);
  return screen.findByRole("dialog", { name: "Fornecedor fictício Alfa" });
}

describe("Excluir", () => {
  it("fornecedor: pede confirmação, cancela sem apagar e, confirmado, apaga e fecha a ficha", async () => {
    const chamadas = simular({ "DELETE /api/fornecedores/1": { status: 200, corpo: { ok: true } } });
    const ficha = await abrirFicha();
    await userEvent.click(within(ficha).getByRole("button", { name: "Excluir fornecedor" }));
    await userEvent.click(within(ficha).getByRole("button", { name: "Cancelar" }));
    expect(chamadas.some((c) => c.metodo === "DELETE")).toBe(false);
    await userEvent.click(within(ficha).getByRole("button", { name: "Excluir fornecedor" }));
    expect(within(ficha).getByRole("group", { name: "Excluir Fornecedor fictício Alfa?" })).toHaveTextContent("Não dá para desfazer");
    await userEvent.click(within(ficha).getByRole("button", { name: "Sim, excluir" }));
    expect(await screen.findByText("Fornecedor fictício Alfa excluído.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(chamadas.filter((c) => c.metodo === "DELETE")).toEqual([{ caminho: "/api/fornecedores/1", metodo: "DELETE" }]);
  });

  it("fornecedor com histórico: mostra a explicação da API e mantém a ficha", async () => {
    const motivo = "Não é possível excluir: o fornecedor tem 1 cotação(ões) registrados.";
    simular({ "DELETE /api/fornecedores/1": { status: 400, corpo: { detail: motivo } } });
    const ficha = await abrirFicha();
    await userEvent.click(within(ficha).getByRole("button", { name: "Excluir fornecedor" }));
    await userEvent.click(within(ficha).getByRole("button", { name: "Sim, excluir" }));
    expect(await within(ficha).findByRole("alert")).toHaveTextContent(motivo);
    expect(screen.getByRole("dialog", { name: "Fornecedor fictício Alfa" })).toBeInTheDocument();
  });

  it("SKU: exclui pela tabela de SKUs e recarrega a ficha", async () => {
    const chamadas = simular({ "DELETE /api/cotacoes/5": { status: 200, corpo: { apagadas: 2 } } });
    const ficha = await abrirFicha();
    await userEvent.click(within(ficha).getByRole("tab", { name: "SKUs cotados (1)" }));
    await userEvent.click(within(ficha).getByRole("button", { name: "Excluir SKU" }));
    await userEvent.click(within(ficha).getByRole("button", { name: "Sim, excluir" }));
    expect(await screen.findByText("SKU KIT-01 excluído.")).toBeInTheDocument();
    const depois = chamadas.slice(chamadas.findIndex((c) => c.metodo === "DELETE"));
    expect(depois.map((c) => `${c.metodo} ${c.caminho}`)).toEqual(expect.arrayContaining(["GET /api/fornecedores/1", "GET /api/fornecedores"]));
  });
});
