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
    expect(screen.queryByText("Valor cobrado pela plataforma sobre cada venda.")).toBeNull();
    fireEvent.mouseEnter(dica);
    expect(screen.getByText("Valor cobrado pela plataforma sobre cada venda.")).toHaveClass("dica-balao");
    expect(screen.getByLabelText("Comissão (%)")).toBeInTheDocument();
    fireEvent.mouseLeave(dica);
    expect(screen.queryByText("Valor cobrado pela plataforma sobre cada venda.")).toBeNull();
  });

  it("toda explicação é curta e preenchida", () => {
    for (const [campo, texto] of Object.entries(DICAS)) {
      expect(texto.trim(), campo).not.toBe("");
      expect(texto.length, campo).toBeLessThanOrEqual(140);
    }
  });
});
