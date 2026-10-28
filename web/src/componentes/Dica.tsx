// "i" ao lado do nome de um campo: ao passar o mouse, ou ao chegar no campo pelo teclado, aparece um
// balão com a explicação. O balão é desenhado fora da gaveta (no fim da página) e posicionado dentro
// da área visível, para não ser cortado no topo nem na borda direita.
// O "i" não tem texto próprio, para o nome do campo continuar o mesmo; para leitores de tela, a
// explicação fica ligada ao campo como descrição (aria-describedby), lida depois do nome.
import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { DICAS, type ChaveDica } from "../dicas";

const LARGURA = 260;
const MARGEM = 8;

type Posicao = { x: number; y: number; abaixo: boolean };

function calcular(alvo: Element): Posicao {
  const r = alvo.getBoundingClientRect();
  const largura = Math.min(LARGURA, window.innerWidth - 2 * MARGEM);
  const x = Math.max(MARGEM, Math.min(r.left - MARGEM, window.innerWidth - largura - MARGEM));
  // Acima do "i" quando há espaço; perto do topo da tela, abaixo dele.
  const abaixo = r.top < 90;
  return { x, y: abaixo ? r.bottom + 7 : r.top - 7, abaixo };
}

export function Dica({ de }: { de: ChaveDica }) {
  const [posicao, setPosicao] = useState<Posicao | null>(null);
  const icone = useRef<HTMLSpanElement>(null);
  const id = useId();

  useEffect(() => {
    // O campo do mesmo rótulo: recebe a descrição e abre o balão ao ganhar foco pelo teclado.
    const campo = icone.current?.closest("label")?.querySelector("input, select, textarea");
    if (!campo) return;
    const anteriores = campo.getAttribute("aria-describedby");
    campo.setAttribute("aria-describedby", [anteriores, id].filter(Boolean).join(" "));
    const abrir = () => { if (icone.current) setPosicao(calcular(icone.current)); };
    const fechar = () => setPosicao(null);
    campo.addEventListener("focus", abrir);
    campo.addEventListener("blur", fechar);
    return () => {
      campo.removeEventListener("focus", abrir);
      campo.removeEventListener("blur", fechar);
      if (anteriores) campo.setAttribute("aria-describedby", anteriores);
      else campo.removeAttribute("aria-describedby");
    };
  }, [id]);

  return (
    <span ref={icone} className="dica" data-dica={DICAS[de]} aria-hidden="true"
      onMouseEnter={(e) => setPosicao(calcular(e.currentTarget))} onMouseLeave={() => setPosicao(null)}>
      {createPortal(
        <span id={id} className={`dica-balao${posicao?.abaixo ? " abaixo" : ""}`} hidden={!posicao}
          style={posicao ? { left: posicao.x, top: posicao.y } : undefined}>
          {DICAS[de]}
        </span>,
        document.body,
      )}
    </span>
  );
}
