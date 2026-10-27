import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Painel, type DadosPainel } from "../src/paginas/Painel";
import { ProvedorNotificacoes } from "../src/componentes/Notificacoes";

const DADOS: DadosPainel = {
  fornecedores_ativos: 3,
  candidatos: 7,
  prontos: 1,
  comprometido_centavos: 18050,
  comprometido_pct: "0.1805",
  orcamento_total_centavos: 100000,
  concluidas: 1,
  tarefas: [
    { id: 1, titulo: "Listar candidatos fictícios", semana: 1, responsavel: "Legacia", concluida: 1 },
    { id: 2, titulo: "Avaliar amostra fictícia", semana: 2, responsavel: "Anna", concluida: 0 },
  ],
  funil: [
    { etapa: "Descoberto", quantidade: 2 }, { etapa: "Em contato", quantidade: 1 },
    { etapa: "Cotado", quantidade: 0 }, { etapa: "Em avaliação", quantidade: 0 },
    { etapa: "Fornecedor oficial", quantidade: 0 }, { etapa: "Descartado ou pausado", quantidade: 0 },
  ],
  pendencias: [
    { tipo: "Amostra pendente", referencia: "Fornecedor fictício Alfa", data: null, responsavel: "Anna" },
    { tipo: "Cotação antiga", referencia: "Incenso · Alfa · INC-01", data: "2026-09-30", responsavel: "Legacia" },
  ],
};

function simular(dados: DadosPainel = DADOS) {
  const chamadas: { caminho: string; init?: RequestInit }[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (entrada, init) => {
    chamadas.push({ caminho: String(entrada), init });
    const corpo = String(entrada) === "/api/painel" ? dados : { id: 2 };
    return new Response(JSON.stringify(corpo), { status: 200 });
  });
  return chamadas;
}

const mostrar = () => render(<ProvedorNotificacoes><Painel /></ProvedorNotificacoes>);

describe("Painel", () => {
  it("mostra os indicadores formatados como vieram da API", async () => {
    simular();
    mostrar();
    expect(await screen.findByText("R$ 180,50")).toBeInTheDocument();
    expect(screen.getByText(/18,1% de R\$ 1\.000,00/)).toBeInTheDocument();
    expect(screen.getByText("Fornecedores ativos").nextSibling).toHaveTextContent("3");
  });

  it("agrupa pendências por responsável, com data brasileira e link para a tela", async () => {
    simular();
    mostrar();
    const anna = (await screen.findByRole("heading", { name: "Anna" })).parentElement!;
    expect(within(anna).getByRole("link", { name: "Fornecedor fictício Alfa" })).toHaveAttribute("href", "#/fornecedores");
    const legacia = screen.getByRole("heading", { name: "Legacia" }).parentElement!;
    expect(legacia).toHaveTextContent("30/09/2026");
    expect(within(legacia).getByRole("link")).toHaveAttribute("href", "#/produtos");
  });

  it("funil tem descrição para leitor de tela, link por etapa e tabela alternativa", async () => {
    simular();
    mostrar();
    const grafico = await screen.findByRole("img", { name: /Descoberto: 2; Em contato: 1/ });
    expect(within(grafico).getByRole("link", { name: "Em contato: 1" })).toHaveAttribute("href", "#/fornecedores?etapa=Em+contato");
    await userEvent.click(screen.getByText("Ver como tabela"));
    expect(screen.getByRole("cell", { name: "Descoberto" }).nextSibling).toHaveTextContent("2");
  });

  it("sem pendências nem fornecedores, mostra mensagens de vazio", async () => {
    simular({ ...DADOS, pendencias: [], funil: DADOS.funil.map((e) => ({ ...e, quantidade: 0 })), comprometido_pct: null });
    mostrar();
    expect(await screen.findByText(/Nenhuma pendência identificada/)).toBeInTheDocument();
    expect(screen.getByText("Nenhum fornecedor cadastrado ainda.")).toBeInTheDocument();
  });

  it("marcar a tarefa envia a mudança e recarrega o painel", async () => {
    const chamadas = simular();
    mostrar();
    await userEvent.click(await screen.findByRole("checkbox", { name: "Avaliar amostra fictícia" }));
    const put = chamadas.find((c) => c.caminho === "/api/tarefas/2")!;
    expect(put.init?.method).toBe("PUT");
    expect(JSON.parse(String(put.init?.body))).toEqual({
      titulo: "Avaliar amostra fictícia", semana: 2, responsavel: "Anna", concluida: true });
    expect(await screen.findByText("Tarefa concluída.")).toBeInTheDocument();
    expect(chamadas.filter((c) => c.caminho === "/api/painel")).toHaveLength(2);
  });

  it("cadastra tarefa pela gaveta", async () => {
    const chamadas = simular();
    mostrar();
    await userEvent.click(await screen.findByRole("button", { name: "Cadastrar tarefa" }));
    const gaveta = screen.getByRole("dialog", { name: "Cadastrar tarefa" });
    await userEvent.type(within(gaveta).getByLabelText("Título da tarefa"), "Cotar suporte fictício");
    await userEvent.selectOptions(within(gaveta).getByLabelText("Semana"), "3");
    await userEvent.click(within(gaveta).getByRole("button", { name: "Salvar tarefa" }));
    const post = chamadas.find((c) => c.caminho === "/api/tarefas")!;
    expect(JSON.parse(String(post.init?.body))).toEqual({
      titulo: "Cotar suporte fictício", semana: 3, responsavel: "Legacia", concluida: false });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("cliques repetidos enquanto salva enviam uma tarefa só", async () => {
    const chamadas = simular();
    mostrar();
    await userEvent.click(await screen.findByRole("button", { name: "Cadastrar tarefa" }));
    const gaveta = screen.getByRole("dialog", { name: "Cadastrar tarefa" });
    await userEvent.type(within(gaveta).getByLabelText("Título da tarefa"), "Tarefa fictícia");
    let liberar!: () => void;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (entrada, init) => {
      chamadas.push({ caminho: String(entrada), init });
      if (String(entrada) === "/api/tarefas") await new Promise<void>((r) => { liberar = r; });
      return new Response(JSON.stringify(String(entrada) === "/api/painel" ? DADOS : { id: 9 }), { status: 200 });
    });
    const salvar = within(gaveta).getByRole("button", { name: "Salvar tarefa" });
    fireEvent.submit(salvar.closest("form")!);
    fireEvent.submit(salvar.closest("form")!);
    fireEvent.submit(salvar.closest("form")!);
    expect(await within(gaveta).findByRole("button", { name: "Salvando…" })).toBeDisabled();
    liberar();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(chamadas.filter((c) => c.caminho === "/api/tarefas")).toHaveLength(1);
  });

  it("caixinha fica travada enquanto a tarefa é salva", async () => {
    const chamadas = simular();
    mostrar();
    const caixa = await screen.findByRole("checkbox", { name: "Avaliar amostra fictícia" });
    let liberar!: () => void;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (entrada, init) => {
      chamadas.push({ caminho: String(entrada), init });
      if (String(entrada).startsWith("/api/tarefas/")) await new Promise<void>((r) => { liberar = r; });
      return new Response(JSON.stringify(String(entrada) === "/api/painel" ? DADOS : { id: 2 }), { status: 200 });
    });
    await userEvent.click(caixa);
    expect(caixa).toBeDisabled();
    expect(screen.getByRole("button", { name: "Editar Avaliar amostra fictícia" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cadastrar tarefa" })).toBeDisabled();
    await userEvent.click(caixa);
    liberar();
    await waitFor(() => expect(caixa).not.toBeDisabled());
    expect(chamadas.filter((c) => c.caminho === "/api/tarefas/2")).toHaveLength(1);
  });

  it("erro da API no formulário aparece na gaveta", async () => {
    simular();
    mostrar();
    await userEvent.click(await screen.findByRole("button", { name: "Editar Listar candidatos fictícios" }));
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Informe o título da tarefa." }), { status: 400 }));
    await userEvent.click(screen.getByRole("button", { name: "Salvar tarefa" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Informe o título da tarefa.");
    expect(screen.getByRole("dialog", { name: "Editar tarefa" })).toBeInTheDocument();
  });
});
