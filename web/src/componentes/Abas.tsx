// Abas acessíveis: setas esquerda/direita trocam de aba, só a aba ativa entra no Tab.
import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";

export function Abas({ rotulo, abas }: { rotulo: string; abas: { titulo: string; conteudo: ReactNode }[] }) {
  const [ativa, setAtiva] = useState(0);
  const base = useId();
  const botoes = useRef<(HTMLButtonElement | null)[]>([]);

  function tecla(e: KeyboardEvent) {
    const passo = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!passo) return;
    e.preventDefault();
    const proxima = (ativa + passo + abas.length) % abas.length;
    setAtiva(proxima);
    botoes.current[proxima]?.focus();
  }

  return (
    <div className="abas">
      <div role="tablist" aria-label={rotulo} className="abas-lista" onKeyDown={tecla}>
        {abas.map((aba, i) => (
          <button key={aba.titulo} type="button" role="tab" id={`${base}-aba-${i}`}
            aria-selected={i === ativa} aria-controls={`${base}-painel-${i}`} tabIndex={i === ativa ? 0 : -1}
            ref={(el) => { botoes.current[i] = el; }} onClick={() => setAtiva(i)}>
            {aba.titulo}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`${base}-painel-${ativa}`} aria-labelledby={`${base}-aba-${ativa}`} className="abas-painel">
        {abas[ativa].conteudo}
      </div>
    </div>
  );
}
