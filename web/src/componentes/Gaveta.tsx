// Gaveta lateral para detalhes (ficha de fornecedor, cotação etc.). Esc fecha, o foco vai para
// dentro ao abrir e volta para onde estava ao fechar.
import { useEffect, useRef, type ReactNode } from "react";

const FOCAVEIS = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function Gaveta({ aberta, titulo, aoFechar, larga, children }: {
  aberta: boolean;
  larga?: boolean;
  titulo: string;
  aoFechar: () => void;
  children: ReactNode;
}) {
  const caixa = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!aberta) return;
    const anterior = document.activeElement as HTMLElement | null;
    caixa.current?.focus();
    const tecla = (e: KeyboardEvent) => {
      if (e.key === "Escape") return aoFechar();
      if (e.key !== "Tab" || !caixa.current) return;
      // Tab e Shift+Tab circulam só pelos controles da gaveta, nunca pelos de trás.
      const focaveis = [...caixa.current.querySelectorAll<HTMLElement>(FOCAVEIS)];
      const [primeiro, ultimo] = [focaveis[0], focaveis[focaveis.length - 1]];
      const atual = document.activeElement;
      if (!primeiro) { e.preventDefault(); return; }
      if (e.shiftKey && (atual === primeiro || atual === caixa.current || !caixa.current.contains(atual))) {
        e.preventDefault(); ultimo.focus();
      } else if (!e.shiftKey && (atual === ultimo || !caixa.current.contains(atual))) {
        e.preventDefault(); primeiro.focus();
      }
    };
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("keydown", tecla);
      anterior?.focus?.();
    };
  }, [aberta, aoFechar]);

  if (!aberta) return null;
  return (
    <div className="gaveta-fundo" onClick={aoFechar}>
      <div className={`gaveta${larga ? " gaveta-larga" : ""}`} role="dialog" aria-modal="true" aria-label={titulo} tabIndex={-1} ref={caixa}
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
