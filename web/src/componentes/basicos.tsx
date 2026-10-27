// Peças pequenas de apresentação, sem regra de negócio.
import type { ReactNode } from "react";

export type Tom = "verde" | "laranja" | "vermelho" | "amarelo" | "azul" | "cinza";

/** Selo colorido: verde cumprido, laranja pendente, vermelho crítico, amarelo atenção, cinza neutro. */
export function Selo({ tom = "cinza", children }: { tom?: Tom; children: ReactNode }) {
  return <span className={`selo selo-${tom}`}>{children}</span>;
}

/** Selos de critérios: ✓ para cumprido, ○ para pendente. */
export function SelosCriterios({ criterios }: { criterios: Record<string, boolean> }) {
  return (
    <ul className="selos" aria-label="Critérios">
      {Object.entries(criterios).map(([nome, ok]) => (
        <li key={nome}>
          <Selo tom={ok ? "verde" : "laranja"}>
            <span aria-hidden="true">{ok ? "✓ " : "○ "}</span>
            {nome}
            <span className="so-leitor">{ok ? ": cumprido" : ": pendente"}</span>
          </Selo>
        </li>
      ))}
    </ul>
  );
}

/** Painel branco com título opcional. */
export function Painel({ titulo, acoes, children }: { titulo?: string; acoes?: ReactNode; children: ReactNode }) {
  return (
    <section className="painel" aria-label={titulo}>
      {(titulo || acoes) && (
        <header className="painel-topo">
          {titulo && <h2>{titulo}</h2>}
          {acoes && <div className="painel-acoes">{acoes}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

/** Cartão de indicador com faixa à esquerda. O valor já chega formatado. */
export function Indicador({ rotulo, valor, detalhe, tom }: { rotulo: string; valor: ReactNode; detalhe?: string; tom?: Tom }) {
  return (
    <div className={`indicador${tom ? " indicador-" + tom : ""}`}>
      <div className="indicador-rotulo">{rotulo}</div>
      <div className="indicador-valor">{valor}</div>
      {detalhe && <div className="indicador-detalhe">{detalhe}</div>}
    </div>
  );
}

export type TipoAviso = "info" | "atencao" | "erro" | "sucesso";

/** Aviso fixo na tela. Erros são anunciados na hora por leitores de tela. */
export function Aviso({ tipo = "info", titulo, children }: { tipo?: TipoAviso; titulo?: string; children: ReactNode }) {
  return (
    <div className={`aviso aviso-${tipo}`} role={tipo === "erro" ? "alert" : "status"}>
      {titulo && <strong>{titulo} </strong>}
      {children}
    </div>
  );
}

export function Cabecalho({ titulo, descricao, acoes }: { titulo: string; descricao?: string; acoes?: ReactNode }) {
  return (
    <header className="cabecalho">
      <div>
        <h1>{titulo}</h1>
        {descricao && <p className="legenda">{descricao}</p>}
      </div>
      {acoes && <div className="cabecalho-acoes">{acoes}</div>}
    </header>
  );
}
