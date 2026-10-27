// Moldura das telas: barra lateral escura com marca, seções e saída; conteúdo à direita.
import { useEffect, useState, type JSX } from "react";
import type { Usuario } from "../api";
import { Aviso, Cabecalho } from "../componentes/basicos";
import { PAGINAS, SECOES, enderecoDe, useRota } from "../rotas";
import { Fornecedores } from "./Fornecedores";
import { Painel } from "./Painel";
import { Produtos } from "./Produtos";

// Telas já migradas; as demais mostram o aviso de construção.
const TELAS: Record<string, () => JSX.Element> = { painel: Painel, fornecedores: Fornecedores, produtos: Produtos };

export function Shell({ usuario, aoSair }: { usuario: Usuario; aoSair: () => Promise<void> }) {
  const rota = useRota();
  const [menuAberto, setMenuAberto] = useState(false);
  const [erroSaida, setErroSaida] = useState<string | null>(null);

  async function tentarSair() {
    setErroSaida(null);
    try {
      await aoSair();
    } catch (erro) {
      const motivo = erro instanceof Error ? erro.message : "";
      setErroSaida(`Não foi possível sair: a sessão continua aberta. ${motivo} Tente de novo.`);
    }
  }
  const pagina = PAGINAS.find((p) => p.chave === rota.pagina)!;
  const Tela = TELAS[pagina.chave];

  useEffect(() => {
    document.title = `${pagina.titulo} · Radar Esotérico`;
    setMenuAberto(false);
  }, [pagina]);

  return (
    <div className="shell">
      <a className="pular" href="#conteudo" onClick={(e) => { e.preventDefault(); document.getElementById("conteudo")?.focus(); }}>
        Pular para o conteúdo
      </a>
      <aside className={`lateral${menuAberto ? " aberta" : ""}`}>
        <div className="lateral-topo">
          <div className="marca">
            <span className="marca-nome">Radar Esotérico</span>
            <span className="marca-sub">Tenda da Bruxa 2.0</span>
          </div>
          <button type="button" className="menu" aria-expanded={menuAberto} aria-controls="navegacao"
            onClick={() => setMenuAberto((v) => !v)}>
            Menu
          </button>
        </div>
        <nav id="navegacao" aria-label="Telas">
          {SECOES.map((secao) => (
            <div key={secao.titulo} className="secao">
              <div className="secao-titulo">{secao.titulo}</div>
              <ul>
                {secao.paginas.map((p) => (
                  <li key={p.chave}>
                    <a href={enderecoDe(p.chave)} aria-current={p.chave === pagina.chave ? "page" : undefined}>
                      {p.titulo}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
        <div className="lateral-pe">
          <div>Conectado: <strong>{usuario.nome}</strong></div>
          <div className="lateral-nota">Sessão de até 8 horas</div>
          <button type="button" className="botao botao-lateral" onClick={tentarSair}>Sair</button>
        </div>
      </aside>
      <main id="conteudo" className="conteudo" tabIndex={-1}>
        {erroSaida && <Aviso tipo="erro">{erroSaida}</Aviso>}
        <Cabecalho titulo={pagina.titulo} descricao={pagina.descricao} />
        {Tela ? <Tela /> : (
          <Aviso titulo="Tela em construção.">
            Esta tela ainda funciona só na versão Streamlit. Ela chega aqui na etapa 3 da migração.
          </Aviso>
        )}
      </main>
    </div>
  );
}
