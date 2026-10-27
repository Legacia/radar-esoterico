import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../src/App";

type Resposta = { status: number; corpo: unknown };

/** Simula a API: cada chamada consome a próxima resposta da lista para aquele caminho. */
function simularApi(respostas: Record<string, Resposta[]>) {
  const chamadas: { caminho: string; init?: RequestInit }[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (entrada, init) => {
    const caminho = String(entrada);
    chamadas.push({ caminho, init });
    const resposta = respostas[caminho]?.shift() ?? { status: 404, corpo: { detail: "Não encontrado." } };
    return new Response(JSON.stringify(resposta.corpo), { status: resposta.status });
  });
  return chamadas;
}

const SEM_SESSAO = { status: 401, corpo: { detail: "Entre novamente para continuar." } };
const ANNA = { status: 200, corpo: { id: 1, nome: "Anna Teste" } };

describe("entrada e sessão", () => {
  it("sem sessão, mostra só a tela de entrada", async () => {
    simularApi({ "/api/eu": [SEM_SESSAO] });
    render(<App />);
    expect(await screen.findByRole("button", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.queryByRole("navigation")).toBeNull();
    expect(screen.queryByText("Sua sessão terminou. Entre novamente.")).toBeNull();
  });

  it("entra, mostra a navegação e envia o cookie da própria origem", async () => {
    const chamadas = simularApi({ "/api/eu": [SEM_SESSAO], "/api/entrar": [ANNA] });
    render(<App />);
    await userEvent.type(await screen.findByLabelText("E-mail"), "anna@exemplo.test");
    await userEvent.type(screen.getByLabelText("Senha"), "senha-ficticia");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("navigation", { name: "Telas" })).toBeInTheDocument();
    expect(screen.getByText("Anna Teste")).toBeInTheDocument();
    const entrar = chamadas.find((c) => c.caminho === "/api/entrar")!;
    expect(entrar.init?.credentials).toBe("same-origin");
    expect(JSON.parse(String(entrar.init?.body))).toEqual({ email: "anna@exemplo.test", senha: "senha-ficticia" });
  });

  it("mostra o erro do servidor e limpa a senha", async () => {
    simularApi({ "/api/eu": [SEM_SESSAO], "/api/entrar": [{ status: 401, corpo: { detail: "E-mail ou senha inválidos." } }] });
    render(<App />);
    await userEvent.type(await screen.findByLabelText("E-mail"), "x@exemplo.test");
    await userEvent.type(screen.getByLabelText("Senha"), "errada");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("E-mail ou senha inválidos.");
    expect(screen.getByLabelText("Senha")).toHaveValue("");
  });

  it("sair com a sessão já vencida também volta à entrada", async () => {
    simularApi({ "/api/eu": [ANNA], "/api/sair": [SEM_SESSAO] });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Sair" }));
    expect(await screen.findByRole("button", { name: "Entrar" })).toBeInTheDocument();
  });

  it("navega pelo endereço e marca a tela atual", async () => {
    simularApi({ "/api/eu": [ANNA] });
    window.location.hash = "#/kits";
    render(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: "Kits" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Kits" })).toHaveAttribute("aria-current", "page");
    window.location.hash = "#/compras";
    expect(await screen.findByRole("heading", { level: 1, name: "Decisão de compra" })).toBeInTheDocument();
  });

  it("sair encerra a sessão no servidor e volta à entrada", async () => {
    const chamadas = simularApi({ "/api/eu": [ANNA], "/api/sair": [{ status: 200, corpo: { ok: true } }] });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Sair" }));
    expect(await screen.findByRole("button", { name: "Entrar" })).toBeInTheDocument();
    expect(chamadas.some((c) => c.caminho === "/api/sair" && c.init?.method === "POST")).toBe(true);
  });

  it("sem conexão ao sair, avisa e mantém a pessoa dentro", async () => {
    simularApi({ "/api/eu": [ANNA] });
    render(<App />);
    const sairBotao = await screen.findByRole("button", { name: "Sair" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    await userEvent.click(sairBotao);
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível sair");
    expect(screen.getByRole("navigation", { name: "Telas" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Entrar" })).toBeNull();
  });

  it("erro do servidor ao sair também não finge que saiu", async () => {
    simularApi({ "/api/eu": [ANNA], "/api/sair": [{ status: 500, corpo: { detail: "Falha interna." } }] });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Sair" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("a sessão continua aberta");
    expect(screen.queryByRole("button", { name: "Entrar" })).toBeNull();
  });

  it("servidor desligado mostra mensagem clara", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    render(<App />);
    await userEvent.type(await screen.findByLabelText("E-mail"), "anna@exemplo.test");
    await userEvent.type(screen.getByLabelText("Senha"), "x");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Sem conexão com o servidor"));
  });
});
