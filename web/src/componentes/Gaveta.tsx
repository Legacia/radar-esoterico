// Gaveta lateral para detalhes (ficha de fornecedor, cotação etc.). Esc fecha, o foco vai para
// dentro ao abrir e volta para onde estava ao fechar.
import { useEffect, useRef, type ReactNode } from "react";

export function Gaveta({ aberta, titulo, aoFechar, children }: {
  aberta: boolean;
  titulo: string;
  aoFechar: () => void;
  children: ReactNode;
}) {
  const caixa = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!aberta) return;
    const anterior = document.activeElement as HTMLElement | null;
    caixa.current?.focus();
    const tecla = (e: KeyboardEvent) => { if (e.key === "Escape") aoFechar(); };
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("keydown", tecla);
      anterior?.focus?.();
    };
  }, [aberta, aoFechar]);

  if (!aberta) return null;
  return (
    <div className="gaveta-fundo" onClick={aoFechar}>
      <div className="gaveta" role="dialog" aria-modal="true" aria-label={titulo} tabIndex={-1} ref={caixa}
        onClick={(e) => e.stopPropagation()}>
        <header className="gaveta-topo">
          <h2>{titulo}</h2>
          <button type="button" className="botao botao-discreto" onClick={aoFechar} aria-label="Fechar">✕</button>
        </header>
        <div className="gaveta-corpo">{children}</div>
      </div>
    </div>
  );
}
