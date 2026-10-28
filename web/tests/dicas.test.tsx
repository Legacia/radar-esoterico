import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { Dica } from "../src/componentes/Dica";
import { DICAS } from "../src/dicas";

describe("Dica do campo", () => {
  it("mostra o \"i\" com a explicação sem mudar o nome do campo", () => {
    render(<label><span className="rotulo">Comissão (%)<Dica de="Comissão (%)" /></span><input /></label>);
    // O nome do campo continua o mesmo para quem usa leitor de tela e para os testes.
    expect(screen.getByLabelText("Comissão (%)")).toBeInTheDocument();
    const dica = document.querySelector(".dica")!;
    expect(dica).toHaveAttribute("data-dica", "Valor cobrado pela plataforma sobre cada venda.");
    expect(dica).toHaveAttribute("aria-hidden", "true");
    // O balão só aparece com o mouse sobre o "i" e some ao sair.
    const balao = () => document.querySelector(".dica-balao")!;
    expect(balao()).not.toBeVisible();
    fireEvent.mouseEnter(dica);
    expect(balao()).toBeVisible();
    expect(balao()).toHaveTextContent("Valor cobrado pela plataforma sobre cada venda.");
    expect(screen.getByLabelText("Comissão (%)")).toBeInTheDocument();
    fireEvent.mouseLeave(dica);
    expect(balao()).not.toBeVisible();
  });

  it("abre pelo teclado e descreve o campo para leitores de tela", () => {
    render(<label><span className="rotulo">Comissão (%)<Dica de="Comissão (%)" /></span><input /></label>);
    const campo = screen.getByRole("textbox", { name: "Comissão (%)" });
    expect(campo).toHaveAccessibleDescription("Valor cobrado pela plataforma sobre cada venda.");
    const balao = document.querySelector(".dica-balao")!;
    fireEvent.focus(campo);
    expect(balao).toBeVisible();
    fireEvent.blur(campo);
    expect(balao).not.toBeVisible();
  });

  it("toda explicação é curta e preenchida", () => {
    for (const [campo, texto] of Object.entries(DICAS)) {
      expect(texto.trim(), campo).not.toBe("");
      expect(texto.length, campo).toBeLessThanOrEqual(140);
    }
  });
});
