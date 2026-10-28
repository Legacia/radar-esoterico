// "i" ao lado do nome de um campo: ao passar o mouse aparece um balão com a explicação.
// O balão é desenhado fora da gaveta (no fim da página) e posicionado dentro da área visível, para
// não ser cortado no topo nem na borda direita. O "i" não tem texto próprio: o nome do campo continua
// o mesmo para leitores de tela.
import { useState } from "react";
import { createPortal } from "react-dom";
import { DICAS, type ChaveDica } from "../dicas";

const LARGURA = 260;
const MARGEM = 8;

export function Dica({ de }: { de: ChaveDica }) {
  const [posicao, setPosicao] = useState<{ x: number; y: number; abaixo: boolean } | null>(null);

  function mostrar(evento: React.MouseEvent<HTMLSpanElement>) {
    const r = evento.currentTarget.getBoundingClientRect();
    const largura = Math.min(LARGURA, window.innerWidth - 2 * MARGEM);
    const x = Math.max(MARGEM, Math.min(r.left - MARGEM, window.innerWidth - largura - MARGEM));
    // Acima do "i" quando há espaço; perto do topo da tela, abaixo dele.
    const abaixo = r.top < 90;
    setPosicao({ x, y: abaixo ? r.bottom + 7 : r.top - 7, abaixo });
  }

  return (
    <span className="dica" data-dica={DICAS[de]} aria-hidden="true" onMouseEnter={mostrar} onMouseLeave={() => setPosicao(null)}>
      {posicao && createPortal(
        <span className={`dica-balao${posicao.abaixo ? " abaixo" : ""}`} style={{ left: posicao.x, top: posicao.y }}>
          {DICAS[de]}
        </span>,
        document.body,
      )}
    </span>
  );
}
