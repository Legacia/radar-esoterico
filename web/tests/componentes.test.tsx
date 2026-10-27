import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { SelosCriterios } from "../src/componentes/basicos";
import { Gaveta } from "../src/componentes/Gaveta";
import { Tabela, type Coluna } from "../src/componentes/Tabela";
import { ProvedorNotificacoes, useNotificar } from "../src/componentes/Notificacoes";

type Linha = { id: number; nome: string; custo: number | null };
const linhas: Linha[] = [
  { id: 1, nome: "Incenso", custo: 250 },
  { id: 2, nome: "Água de rosas", custo: null },
  { id: 3, nome: "Cristal", custo: 1200 },
];
const colunas: Coluna<Linha>[] = [
  { chave: "nome", titulo: "Produto", mostrar: (l) => l.nome, ordenar: (l) => l.nome },
  { chave: "custo", titulo: "Custo", mostrar: (l) => String(l.custo), ordenar: (l) => l.custo },
];
const nomes = () => screen.getAllByRole("row").slice(1).map((r) => r.firstChild?.textContent);

describe("Tabela", () => {
  it("ordena ao clicar no título e deixa vazios no fim", async () => {
    render(<Tabela titulo="Produtos" colunas={colunas} linhas={linhas} chaveLinha={(l) => l.id} />);
    await userEvent.click(screen.getByRole("button", { name: /Produto/ }));
    expect(nomes()).toEqual(["Água de rosas", "Cristal", "Incenso"]);
    await userEvent.click(screen.getByRole("button", { name: /Custo/ }));
    expect(nomes()).toEqual(["Incenso", "Cristal", "Água de rosas"]);
    await userEvent.click(screen.getByRole("button", { name: /Custo/ }));
    expect(nomes()).toEqual(["Cristal", "Incenso", "Água de rosas"]);
    expect(screen.getByRole("columnheader", { name: /Custo/ })).toHaveAttribute("aria-sort", "descending");
  });

  it("mostra mensagem quando não há linhas", () => {
    render(<Tabela titulo="Produtos" colunas={colunas} linhas={[]} chaveLinha={(l) => l.id} vazio="Sem produtos." />);
    expect(screen.getByText("Sem produtos.")).toBeInTheDocument();
  });

  it("abre a linha pelo teclado", async () => {
    const aoClicar = vi.fn();
    render(<Tabela titulo="Produtos" colunas={colunas} linhas={linhas} chaveLinha={(l) => l.id} aoClicar={aoClicar} />);
    screen.getAllByRole("row")[1].focus();
    await userEvent.keyboard("{Enter}");
    expect(aoClicar).toHaveBeenCalledWith(linhas[0]);
  });
});

describe("Gaveta", () => {
  function Exemplo() {
    const [aberta, setAberta] = useState(false);
    return (
      <>
        <button onClick={() => setAberta(true)}>Abrir ficha</button>
        <Gaveta aberta={aberta} titulo="Ficha" aoFechar={() => setAberta(false)}>
          <input aria-label="Nome" />
        </Gaveta>
      </>
    );
  }

  it("Esc fecha e o foco volta ao botão", async () => {
    render(<Exemplo />);
    await userEvent.click(screen.getByText("Abrir ficha"));
    expect(screen.getByRole("dialog", { name: "Ficha" })).toHaveFocus();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByText("Abrir ficha")).toHaveFocus();
  });

  it("Tab e Shift+Tab não saem da gaveta", async () => {
    render(<Exemplo />);
    await userEvent.click(screen.getByText("Abrir ficha"));
    const fechar = screen.getByRole("button", { name: "Fechar" });
    const nome = screen.getByLabelText("Nome");
    await userEvent.tab({ shift: true });
    expect(nome).toHaveFocus();
    await userEvent.tab();
    expect(fechar).toHaveFocus();
    await userEvent.tab();
    expect(nome).toHaveFocus();
    await userEvent.tab();
    expect(fechar).toHaveFocus();
    await userEvent.tab({ shift: true });
    expect(nome).toHaveFocus();
  });
});

describe("Selos e notificações", () => {
  it("diz ao leitor de tela o que está cumprido", () => {
    render(<SelosCriterios criterios={{ Fornecedor: true, Demanda: false }} />);
    const itens = screen.getAllByRole("listitem").map((i) => i.textContent);
    expect(itens).toEqual(["✓ Fornecedor: cumprido", "○ Demanda: pendente"]);
  });

  it("mostra e fecha uma notificação", async () => {
    function Botao() {
      const notificar = useNotificar();
      return <button onClick={() => notificar("Fornecedor salvo.")}>Salvar</button>;
    }
    render(<ProvedorNotificacoes><Botao /></ProvedorNotificacoes>);
    await userEvent.click(screen.getByText("Salvar"));
    expect(screen.getByText("Fornecedor salvo.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Fechar aviso" }));
    expect(screen.queryByText("Fornecedor salvo.")).toBeNull();
  });
});
